#! /usr/bin/python3
# (c) Copyright 2019-2024, James Stevens ... see LICENSE for details
# Alternative license arrangements possible, contact me for more information
""" entry point for running web/ui rest/api - called by start-yp shell scr """

from flask_promyq import application

if __name__ == "__main__":
    application.run()
