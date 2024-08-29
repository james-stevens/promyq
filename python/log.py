#! /usr/bin/python3
# (c) Copyright 2019-2022, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" functions for sys-logging """

import syslog

facility_options = {
    "kern": syslog.LOG_KERN,
    "kernel": syslog.LOG_KERN,
    "user": syslog.LOG_USER,
    "mail": syslog.LOG_MAIL,
    "daemon": syslog.LOG_DAEMON,
    "auth": syslog.LOG_AUTH,
    "syslog": syslog.LOG_SYSLOG,
    "lpr": syslog.LOG_LPR,
    "news": syslog.LOG_NEWS,
    "uucp": syslog.LOG_UUCP,
    "cron": syslog.LOG_CRON,
    "authpriv": syslog.LOG_AUTHPRIV,
    "local0": syslog.LOG_LOCAL0,
    "local1": syslog.LOG_LOCAL1,
    "local2": syslog.LOG_LOCAL2,
    "local3": syslog.LOG_LOCAL3,
    "local4": syslog.LOG_LOCAL4,
    "local5": syslog.LOG_LOCAL5,
    "local6": syslog.LOG_LOCAL6,
    "local7": syslog.LOG_LOCAL7
}

severity_options = {
    "emerg": syslog.LOG_EMERG,
    "emergency": syslog.LOG_EMERG,
    "alert": syslog.LOG_ALERT,
    "crit": syslog.LOG_CRIT,
    "critical": syslog.LOG_CRIT,
    "err": syslog.LOG_ERR,
    "error": syslog.LOG_ERR,
    "warning": syslog.LOG_WARNING,
    "notice": syslog.LOG_NOTICE,
    "info": syslog.LOG_INFO,
    "information": syslog.LOG_INFO,
    "debug": syslog.LOG_DEBUG
}
