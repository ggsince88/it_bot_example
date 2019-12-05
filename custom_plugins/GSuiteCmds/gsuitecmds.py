import os
import yaml
import json
import datetime
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from itertools import chain
from errbot import BotPlugin, botcmd, arg_botcmd, ValidationException


class GSuiteCmds(BotPlugin):
    """Errbot plugin to run GSuite commands using the Google API."""

    GOOGLE_SCOPES = [
        'https://mail.google.com/',
        'https://www.googleapis.com/auth/gmail.settings.sharing',
        'https://www.googleapis.com/auth/gmail.settings.basic',
        'https://www.googleapis.com/auth/admin.directory.user',
        'https://www.googleapis.com/auth/admin.datatransfer'
    ]

    SERVICE_ACCOUNT = "service@test.com"


    def activate(self):
        super().activate()
        self.vault_url = 'http://vault.gsuite.test.com'

    def auth_google(self, scopes, service_name, service_version, target_email=None):
        """Setup authentication with Google."""
        if target_email is None:
            target_email = self.SERVICE_ACCOUNT
        try:
            gsuite_api_auth = self.bot_config.GOOGLE_CONFIG
            credential = service_account.Credentials.from_service_account_info(gsuite_api_auth,
                                                                               subject=target_email, scopes=scopes)
        except AttributeError:
            # creds file is stored in DATA dir for errbot
            # self.outdir = self.bot_config.BOT_DATA_DIR
            self.outdir = self.bot_config.BOT_EXTRA_PLUGIN_DIR
            gsuite_api_auth = os.path.join(
                self.outdir, "./GSuiteCmds/service_secret.json")
            credential = service_account.Credentials.from_service_account_file(gsuite_api_auth,
                                                                               subject=target_email, scopes=scopes)

        gsuite_service_connection = build(
            service_name, service_version, credentials=credential)
        return gsuite_service_connection

    def format_response(self, data):
        """Format Google response as yaml."""
        if data:
            return yaml.dump(data, default_flow_style=False)
        else:
            self.log.info("data returned false. Value if any is (%s)", data)
            return "No results returned."

    @arg_botcmd('--userid', '-u', dest='user_id', type=str, required=True)
    def list_forwarding(self, msg, user_id):
        """
        List forwarding addresses and status for a user.

        Use primary email address for userid argument.
        """
        gsuite = self.auth_google(self.GOOGLE_SCOPES, 'gmail', 'v1', user_id)
        try:
            data = gsuite.users().settings().forwardingAddresses().list(userId=user_id).execute()
            yield self.format_response(data)
        except HttpError as err:
            self.log.exception(err)
            yield err

    @arg_botcmd('--userid', '-u', dest='user_id', type=str, required=True)
    def list_delegates(self, msg, user_id):
        """
        List delegates for a user.

        Use primary email address for userid argument.
        """
        gsuite = self.auth_google(self.GOOGLE_SCOPES, 'gmail', 'v1', user_id)
        try:
            data = gsuite.users().settings().delegates().list(userId=user_id).execute()
            yield "Getting delegates..."
            yield self.format_response(data)
        except HttpError as err:
            self.log.exception(err)
            yield err

    @arg_botcmd('--email', '-e', dest='email_address', type=str, required=True)
    def add_export(self, msg, email_address: str) -> str:
        try:
            response = requests.get(self.vault_url + '/export/add/?email=' + email_address)
            assert response.status_code == 200
        except AssertionError:
            return 'ERROR: FAILED TO ADD: ' + email_address
        except Exception:
            return 'ERROR: UNEXPECTED ERROR: ' + email_address
        return 'OK: Added email to the queue for processing.\n- ' + email_address

    @arg_botcmd('--email', '-e', dest='email_address', type=str, required=True)
    def list_export(self, msg, email_address: str) -> str:
        try:
            response = requests.get(self.vault_url + '/export/list/?email=' + email_address)
            assert response.status_code == 200
        except AssertionError:
            return 'ERROR: FAILED TO LIST'
        except Exception:
            return 'ERROR: UNEXPECTED ERROR'
        return response.text

    @arg_botcmd('--userid', '-u', dest='user_id', type=str, required=True)
    @arg_botcmd('--to', '-t', dest='target_id', type=str, required=True)
    def add_delegate(self, msg, user_id, target_id):
        """
        Add delegate for user. Commonly used for terms.

        Ex. !add delegate --userid termed_user@test.com --to manager@test.com
        """
        gsuite = self.auth_google(self.GOOGLE_SCOPES, 'gmail', 'v1', user_id)
        body = {'delegateEmail': target_id}
        try:
            data = gsuite.users().settings().delegates().create(
                userId='me', body=body).execute()
            yield "Adding delegates..."
            yield self.format_response(data)
        except HttpError as err:
            self.log.exception(err)
            yield err

    @arg_botcmd('--userid', '-u', dest='user_id', type=str, required=True)
    @arg_botcmd('--to', '-t', dest='target_id', type=str, required=True)
    def add_forwarding(self, msg, user_id, target_id):
        """
        Add forwarding address for a user

        Ex. !add forwarding --userid user@eastridge,cin --to manager@test.com
        """
        gsuite = self.auth_google(self.GOOGLE_SCOPES, 'gmail', 'v1', user_id)
        body = {'forwardingEmail': target_id}
        try:
            data = gsuite.users().settings().forwardingAddresses().create(
                userId='me', body=body).execute()
            yield "Adding Forwarding address..."
            yield self.format_response(data)
            yield self.format_response(self.update_forwarding(True, user_id, target_id))
        except HttpError as err:
            self.log.exception(err)
            yield err

    def update_forwarding(self, enabled, user_id, target_id, disposition='leaveInInbox'):
        gsuite = self.auth_google(self.GOOGLE_SCOPES, 'gmail', 'v1', user_id)
        body = {
            'emailAddress': target_id,
            'disposition': disposition,
            'enabled': enabled
        }
        data = gsuite.users().settings().updateAutoForwarding(userId='me', body=body).execute()
        return data

    @arg_botcmd('--userid', '-u', dest='user_id', type=str, required=True)
    @arg_botcmd('--to', '-t', dest='target_id', type=str, required=True)
    def remove_delegate(self, msg, user_id, target_id):
        """
        Remove delegate from user.

        Ex. !remove delegate --userid user@eastridge --to manager@test.com
        """
        gsuite = self.auth_google(self.GOOGLE_SCOPES, 'gmail', 'v1', user_id)
        try:
            # If successful Google API will return nothing
            data = gsuite.users().settings().delegates().delete(
                userId='me', delegateEmail=target_id).execute()
            yield data
            yield "Done!"
        except HttpError as err:
            self.log.exception(err)
            yield err

    @arg_botcmd('--userid', '-u', dest='user_id', type=str, required=True)
    @arg_botcmd('--to', '-t', dest='target_id', type=str, required=True)
    def remove_forwarding(self, msg, user_id, target_id):
        """
        Remove forwarding from user.

        Ex. !remove forwarding --userid user@eastridge --to manager@test.com
        """
        gsuite = self.auth_google(self.GOOGLE_SCOPES, 'gmail', 'v1', user_id)
        try:
            # If successful Google API will return nothing
            data = gsuite.users().settings().forwardingAddresses().delete(
                userId='me', forwardingEmail=target_id).execute()
            yield data
            yield "Done!"
        except HttpError as err:
            self.log.exception(err)
            yield err

    def query_user_info(self, user_id, user_fields):
        try:
            gsuite = self.auth_google(
                self.GOOGLE_SCOPES, 'admin', 'directory_v1')
            data = gsuite.users().get(userKey=user_id, fields=user_fields, projection='full').execute()
            self.log.info(data)
            return data
        except HttpError as err:
            self.log.exception(err)
            return err

    @arg_botcmd('--userid', '-u', dest='user_id', type=str, required=True)
    @arg_botcmd('--fields', '-f', dest='user_fields', type=str, default="aliases,suspended")
    def get_userinfo(self, msg, user_id, user_fields=None):
        """
        Get user's info from Google Directory such as suspended status or aliases.
        Returns Aliases and Suspended status by default. Other fields can be returned
        such as orgUnitPath. Refer to https://developers.google.com/admin-sdk/directory/v1/reference/users
        for more fields.

        EXAMPLE - !get userinfo -u user@test.com EXAMPLE - !get userinfo -u USER -f suspended,suspensionReason,primaryEmail
        """
        return self.format_response(self.query_user_info(user_id, user_fields))
        # suspended,suspensionReason,primaryEmail,relations,orgUnitPath,name,aliases,lastLoginTime

    @arg_botcmd('--userid', '-u', dest='user_id', type=str, required=True)
    def get_ooo(self, msg, user_id):
        """
        Get user's Out Of Office message (AKA Vacation).

        EXAMPLE - !get ooo -u USER
        """
        try:
            gsuite = self.auth_google(
                self.GOOGLE_SCOPES, 'gmail', 'v1', user_id)
            data = gsuite.users().settings().getVacation(userId=user_id).execute()
            # https://docs.python.org/3.4/library/datetime.html#strftime-strptime-behavior
            try:
                data["startTime"] = datetime.datetime.fromtimestamp(
                    int(data["startTime"]) / 1000.0).strftime('%c')
                data["endTime"] = datetime.datetime.fromtimestamp(
                    int(data["endTime"]) / 1000.0).strftime('%c')
            except KeyError as err:
                pass
            return self.format_response(data)
        except HttpError as err:
            self.log.exception(err)
            return err

    @arg_botcmd('--userid', '-u', dest='user_id', type=str, required=True)
    @arg_botcmd('--responseBody', '-r', dest='response_body', type=str)
    @arg_botcmd('--responseSubject', '-s', dest='response_subject', type=str, default='Out of Office')
    @arg_botcmd('--disableAutoReply', '-d', dest='enable_autoreply', action='store_false')
    @arg_botcmd('--enableAutoReply', '-e', dest='enable_autoreply', default=False, action='store_true')
    def update_ooo(self, msg, user_id, response_body, response_subject, enable_autoreply):
        """
        BETA - Update user's OOO settings and message. Need to pass -e flag to
        enable auto reply. By default auto reply will be disabled.

        EXAMPLE - !update ooo USER --enableAutoReply --
        """
        try:
            gsuite = self.auth_google(
                self.GOOGLE_SCOPES, 'gmail', 'v1', user_id)
            self.log.info("enable_autoreply is %s", enable_autoreply)
            body = {}
            body['enableAutoReply'] = enable_autoreply
            body['responseSubject'] = response_subject
            body['responseBodyPlainText'] = response_body
            # body['startTime'] = int(datetime.datetime.now().timestamp() * 1000)
            if not enable_autoreply:
                yield "WARNING: Auto Reply is DISABLED."
            data = gsuite.users().settings().updateVacation(
                userId=user_id, body=body).execute()
            yield "Success!"
            yield self.format_response(data)
        except HttpError as err:
            self.log.exception(err)
            return err

    def get_transfer_app_info(self, app):
        """
        Get app info from Google using ID or App name. This is subject to
        change which is why this function exists instead of hardcoding the app
        IDs.
        """
        try:
            gsuite = self.auth_google(
                self.GOOGLE_SCOPES, 'admin', 'datatransfer_v1')
            data = gsuite.applications().list().execute()
            app_data = next(
                i for i in data["applications"] if i["name"] == app or i["id"] == app)
            return app_data
        except HttpError as err:
            self.log.exception(err)
            return err

    def query_transfer_status(self, id):
        try:
            gsuite = self.auth_google(
                self.GOOGLE_SCOPES, 'admin', 'datatransfer_v1')
            data = gsuite.transfers().get(dataTransferId=id).execute()
            return data
        except HttpError as err:
            self.log.exception(err)
            return err

    def list_transfer_status(self, user_id):
        try:
            gsuite = self.auth_google(
                self.GOOGLE_SCOPES, 'admin', 'datatransfer_v1')
            data = gsuite.transfers().list(oldOwnerUserId=user_id).execute()
            return data
        except HttpError as err:
            self.log.exception(err)
            return err

    def check_transfer_complete(self, id, channel):
        self.log.info(id)
        data = self.query_transfer_status(id)
        transfer_status = data['overallTransferStatusCode']
        if transfer_status == 'completed':
            message = 'Transfer status is completed. Stopping poller...'
            self.log.info(message)
            self.stop_poller(self.check_transfer_complete, [id, channel])
            self.send(self.build_identifier(channel), self.format_response(data))
            self.send(self.build_identifier(channel), message)
        elif transfer_status == 'failed':
            message = 'Transfer failed. Stopping poller...'
            self.log.warning(message)
            self.stop_poller(self.check_transfer_complete, [id, channel])
            self.send(self.build_identifier(channel), self.format_response(data))
            self.send(self.build_identifier(channel), message)

    @arg_botcmd('--userid', '-u', dest='user_id', type=str, required=True)
    @arg_botcmd('--to', '-t', dest='target_id', type=str, required=True)
    @arg_botcmd('--app', '-a', dest='app', type=str, required=True, choices=['drive','calendar'])
    def create_transfer(self, msg, user_id, target_id, app):
        """
        Transfer all shared and private drive contents. Used normally after term.
        EXAMPLE -- !create transfer -u termed@test.com -t manager@test.com
        """
        try:
            old_user = self.query_user_info(user_id, 'id,orgUnitPath')
            if '/Suspended' not in old_user['orgUnitPath']:
                self.log.warning('ERROR: {} must be in Suspended OU.'.format(user_id))
                return 'ERROR: {} must be in Suspended OU.'.format(user_id)
            new_user = self.query_user_info(target_id, 'id,orgUnitPath')
            available_apps = {'drive': 'Drive and Docs', 'calendar': 'Calendar'}
            app_info = self.get_transfer_app_info(available_apps.get(app))
            body = {}
            body['oldOwnerUserId'] = old_user['id']
            body['newOwnerUserId'] = new_user['id']
            body['applicationDataTransfers'] = [
                {
                    'applicationId': app_info['id'],
                    'applicationTransferParams': app_info['transferParams']
                }
            ]
            gsuite = self.auth_google(
                self.GOOGLE_SCOPES, 'admin', 'datatransfer_v1')
            data = gsuite.transfers().insert(body=body).execute()
            yield self.format_response(data)
            self.log.info(data)
            channel = str(msg.frm).split('/')[0]
            self.start_poller(
                300, self.check_transfer_complete, 10, [data['id'], channel])
            yield "Started poller to check if transfer completed in 5 minutes"
        except HttpError as err:
            self.log.exception(err)
            return err

    @arg_botcmd('--userid', '-u', dest='user_id', type=str, required=True)
    @arg_botcmd('--verbose', '-v', dest='verbose', default=False, action='store_true')
    def get_transfer_status(self, msg, user_id, verbose):
        user_google_id = self.query_user_info(user_id, 'id')['id']
        data = self.list_transfer_status(user_google_id)
        for item in data['dataTransfers']:
            if verbose:
                yield self.format_response(item['applicationDataTransfers'])
            yield 'Transfer status: {}\nRequest Time: {}\n'.format(item['overallTransferStatusCode'], item['requestTime'])
