FROM rroemhild/errbot
COPY config_PROD.py /etc/errbot/
COPY custom_plugins/ /etc/errbot/custom_plugins/
# MarkDown 2.6.11 resolves issue with errbot storing creds
# https://github.com/errbotio/errbot/issues/1255
RUN pip install --force-reinstall Markdown==2.6.11
CMD ["-c /etc/errbot/config_PROD.py"]
