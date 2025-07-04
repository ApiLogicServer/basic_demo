#!/usr/bin/env python3

###############################################################################
#
#    Initalization functions used by api_logic_server_run.py
#
#    You typically do not customize this file,
#        except to override Creation Defaults and Logging, below.
#
###############################################################################

"""
Operation:
    1. api_logic_server_run.py - imports config
        1. captures args
    2. api_logic_server_run.py - imports server_setup
        1. server_setup#logging_setup()
    3. api_logic_server_run.py - server_setup.api_logic_server_setup
On error, NOT CALLED: constraint_handler or ValidationErrorExt (!)

+ Operation:
    1. api_logic_server_run.py - imports config
        1. captures args
        1. config#logging_setup()
    2. api_logic_server_run.py - imports server_setup
    3. api_logic_server_run.py - server_setup.api_logic_server_setup

"""

start_up_message = "normal start"

import traceback
try:
    import os, logging, logging.config, sys, yaml  # failure here means venv probably not set
except:
    track = traceback.format_exc()
    print(" ")
    print(track)
    print("venv probably not set")
    print("Please see https://apilogicserver.github.io/Docs/Project-Env/ \n")
    exit(1)

from flask_sqlalchemy import SQLAlchemy
import json
from pathlib import Path
if os.getenv("EXPERIMENT") == '+':
    import config
from config.config import Args


setup_path = Path(os.path.abspath(os.path.dirname(__file__)))
project_path = setup_path.parent


def is_docker() -> bool:
    """ running docker?  dir exists: /home/api_logic_server """
    path = '/home/api_logic_server'
    path_result = os.path.isdir(path)  # this *should* exist only on docker
    env_result = "DOCKER" == os.getenv('APILOGICSERVER_RUNNING')
    # assert path_result == env_result
    return path_result


if is_docker():
    sys.path.append(os.path.abspath('/home/api_logic_server'))

logic_alerts = True
""" Set False to silence startup message """
declare_logic_message = ""
declare_security_message = "ALERT:  *** Security Not Enabled ***"

project_dir = str(project_path)
os.chdir(project_dir)  # so admin app can find images, code
import api.system.api_utils as api_utils
logic_logger_activate_debug = False
""" True prints all rules on startup """

args = ""
arg_num = 0
for each_arg in sys.argv:
    args += each_arg
    arg_num += 1
    if arg_num < len(sys.argv):
        args += ", "
project_name = os.path.basename(os.path.normpath(project_path))

from typing import TypedDict
import safrs  # fails without venv - see https://apilogicserver.github.io/Docs/Project-Env/
from safrs import ValidationError, SAFRSBase, SAFRSAPI as _SAFRSAPI
from logic_bank.logic_bank import LogicBank
from logic_bank.exceptions import LBActivateException
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.rule_type.constraint import Constraint
from .activate_logicbank import activate_logicbank
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
import socket
import warnings
from flask import Flask, redirect, send_from_directory, send_file
from flask_cors import CORS
from safrs import ValidationError, SAFRSBase, SAFRSAPI
import ui.admin.admin_loader as AdminLoader
from security.system.authentication import configure_auth
import database.bind_dbs as bind_dbs
import oracledb
import integration.kafka.kafka_producer as kafka_producer
import integration.kafka.kafka_consumer as kafka_consumer
import integration.n8n.n8n_producer as n8n_producer


if os.getenv("EXPERIMENT") == '+':
    app_logger = logging.getLogger("api_logic_server_app")


class SAFRSAPI(_SAFRSAPI):
    """
    Extends SAFRSAPI to handle client_uri

    Args:
        _SAFRSAPI (_type_): _description_
    """

    def __init__(self, *args, **kwargs):
        client_uri = kwargs.pop('client_uri', None)
        if client_uri:
            kwargs['port'] = None
            kwargs['host'] = client_uri
        super().__init__(*args, **kwargs)



# ==================================
#       Set
# ================================== 

def get_args(flask_app: Flask) -> Args:
    """
    Get Args, update logging

    Returns:
        Args: typed access to flask_app.config
    """
    args = Args(flask_app=flask_app)                                # creation defaults

    import config.config as config
    flask_app.config.from_object(config.Config)
    app_logger.debug(f"\nserver_setup - get_args: Config args: \n{args}")  #                 # config file (e.g., db uri's)

    args.get_cli_args(dunder_name=__name__, args=args)
    app_logger.debug(f"\nserver_setup - get_args: CLI args: \n{args}")                       # api_logic_server_run cl args

    flask_app.config.from_prefixed_env(prefix="APILOGICPROJECT")    # env overrides (e.g., docker)
    app_logger.debug(f"\nserver_setup - get_args: ENV args: \n{args}\n\n")

    if args.verbose:  # export APILOGICPROJECT_VERBOSE=True
        app_logger.setLevel(logging.DEBUG)
        safrs.log.setLevel(logging.DEBUG)  # notset 0, debug 10, info 20, warn 30, error 40, critical 50
        authentication_logger = logging.getLogger('security.system.authentication')
        authentication_logger.setLevel(logging.DEBUG)
        authorization_logger = logging.getLogger('security.system.authorization')
        authorization_logger.setLevel(logging.DEBUG)
        auth_provider_logger = logging.getLogger('security.authentication_provider.sql.auth_provider')
        auth_provider_logger.setLevel(logging.DEBUG)
        # sqlachemy_logger = logging.getLogger('sqlalchemy.engine')
        # sqlachemy_logger.setLevel(logging.DEBUG)

    if app_logger.getEffectiveLevel() <= logging.DEBUG:
        api_utils.sys_info(flask_app.config)
    app_logger.debug(f"\nserver_setup - get_args: ENV args: \n{args}\n\n")
    return args


# ==================================
#       LOGGING SETUP
# ================================== 

import site

# Auto-detect venv site-packages path
import logging
import site

venv_path = site.getsitepackages()[0]
venv_alias = "$venv"
app_path = str(Path(__file__).parent.parent)
app_alias = ""
max_len = 100  # max length of a line in stacktrace

# Patch stacktrace formatters to replace venv path with alias
def patch_stacktrace_formatters():
    """
    Patch only the formatException method of each formatter,
    so only stacktraces are affected, not normal log lines.
    """
    import logging

    def short_format_exception(self, exc_info):
        result = logging.Formatter.formatException(self, exc_info)
        lines = result.splitlines('\n')
        line_num = 0
        for each_line in lines:
            follow_link = ""
            if '1906' in each_line:
                pass # good breakpoint
            if venv_path in each_line:                
                # get the string inside the double quotes
                if '"' in each_line:
                    follow_link = '\tFollow link: ' + each_line.split('"')[1] + ']'
                # Replace the venv_path with venv_alias in the stacktrace line
                each_line = each_line.replace('"' + venv_path, venv_alias)
                each_line = each_line.replace('File ', '')  # replace project path with name
                each_line = each_line.replace('", line ', ' @ ')
                each_line = each_line.replace('^', '')
                each_line = each_line.replace('\n', '')
                lines[line_num] = each_line
            elif app_path in each_line:
                if '"' in each_line:
                    follow_link = '\tFollow link: ' + each_line.split('"')[1] + ']'
                each_line = each_line.replace('"' + app_path, app_alias)
                each_line = each_line.replace('File ', '')
                each_line = each_line.replace('", line ', ' @ ')
                each_line = each_line.replace('\n', '')
                lines[line_num] = each_line
            elif '^^' in each_line:
                lines[line_num] = ""
            elif 'File "<string>", line' in each_line:
                lines[line_num] = ""
            # add spaces for 90 characters
            if len(lines[line_num]) < max_len and lines[line_num] != "" and follow_link != "":
                lines[line_num] = lines[line_num] + ' ' * (max_len - len(lines[line_num]))
            lines[line_num] += follow_link
            line_num += 1
        result = ''.join(lines)
        return result
    
    # Patch the formatException method of all formatters in the root logger

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        fmt = handler.formatter
        if fmt and not hasattr(fmt, "_stacktrace_patched"):
            fmt.formatException = short_format_exception.__get__(fmt)
            fmt._stacktrace_patched = True


def logging_setup() -> logging.Logger:
    """
    Setup Logging
    """
    global app_logger, debug_value, project_path
    logging_config = f'{project_path}/config/logging.yml'
    if os.getenv('APILOGICPROJECT_LOGGING_CONFIG'):
        logging_config = project_path.joinpath(os.getenv("APILOGICPROJECT_LOGGING_CONFIG"))
    with open(logging_config,'rt') as f:  # see also logic/declare_logic.py
            config=yaml.safe_load(f.read())
            f.close()
    logging.config.dictConfig(config)  # log levels: notset 0, debug 10, info 20, warn 30, error 40, critical 50
    app_logger = logging.getLogger("api_logic_server_app")

    if do_truncate_venv_path := True:   # use False for standard Python logging in stacktrace
        patch_stacktrace_formatters()

    debug_value = os.getenv('APILOGICPROJECT_DEBUG')
    if debug_value is not None:  # > export APILOGICPROJECT_DEBUG=True
        debug_value = debug_value.upper()
        if debug_value.startswith("F") or debug_value.startswith("N"):
            app_logger.setLevel(logging.INFO)
        else:
            app_logger.setLevel(logging.DEBUG)
            app_logger.debug(f'\nDEBUG level set from env\n')
    app_logger.info(f'\nAPI Logic Project Server Setup ({project_name}) Starting with CLI args: \n.. {args}\n')
    app_logger.info(f'Created August 03, 2024 09:34:01 at {str(project_path)}\n') 
    return app_logger  


class ValidationErrorExt(ValidationError):
    """
    This exception is raised when invalid input has been detected (client side input)
    Always send back the message to the client in the response
    """

    def __init__(self, message="", status_code=400, api_code=2001, detail=None, error_attributes=None):
        Exception.__init__(self)
        self.error_attributes = error_attributes
        self.status_code = status_code
        self.message = message
        self.api_code = api_code
        self.detail: TypedDict = detail


def validate_db_uri(flask_app):
    """

    For sqlite, verify the SQLALCHEMY_DATABASE_URI file exists

        * Since the name is not reported by SQLAlchemy

    Args:
        flask_app (_type_): initialize flask app
    """

    db_uri = flask_app.config['SQLALCHEMY_DATABASE_URI']
    app_logger.debug(f'sqlite_db_path validity check with db_uri: {db_uri}')
    if 'sqlite' not in db_uri:
        return
    sqlite_db_path = ""
    if db_uri.startswith('sqlite:////'):  # eg, sqlite:////Users/val/dev/ApiLogicServer/ApiLogicServer-dev/servers/ai_customer_orders/database/db.sqlite
        sqlite_db_path = Path(db_uri[9:])
        app_logger.debug(f'\t.. Absolute: {str(sqlite_db_path)}')
    else:                                # eg, sqlite:///../database/db.sqlite
        db_relative_path = db_uri[10:]
        db_relative_path = db_relative_path.replace('../', '') # relative
        sqlite_db_path = Path(os.getcwd()).joinpath(db_relative_path)
        app_logger.debug(f'\t.. Relative: {str(sqlite_db_path)}')
        if db_uri == 'sqlite:///database/db.sqlite':
            raise ValueError(f'This fails, please use; sqlite:///../database/db.sqlite')
    if sqlite_db_path.is_file():
        app_logger.debug(f'\t.. sqlite_db_path is a valid file\n')
    else:  # remove this if you wish
        raise ValueError(f'sqlite database does not exist: {str(sqlite_db_path)}')



# ==========================================================
# API Logic Server Setup
#   - Opens Database(s)
#   - Setup API, Logic, Security, Optimistic Locking 
# ==========================================================

def api_logic_server_setup(flask_app: Flask, args: Args):
    """
    API Logic Server Setup

    1. Opens Database(s)
    2. Setup API, Logic, Security, Optimistic Locking


    Args:
        flask_app (_type_): configured flask_app (servers, ports, db uri's)
        args (_type_): typed access to flask_app.config

    Raises:
        ValidationErrorExt: rebadge LogicBank errors for SAFRS API
    """

    from sqlalchemy import exc as sa_exc

    global logic_logger_activate_debug, declare_logic_message, declare_security_message

    with warnings.catch_warnings():

        safrs_log_level = safrs.log.getEffectiveLevel()
        db_logger = logging.getLogger('sqlalchemy')
        db_log_level = db_logger.getEffectiveLevel()
        safrs_init_logger = logging.getLogger("safrs.safrs_init")
        authorization_logger = logging.getLogger('security.system.authorization')
        authorization_log_level = authorization_logger.getEffectiveLevel()
        do_hide_chatty_logging = True and not args.verbose
        # eg, system startup health check: read on API and relationship - hide many log entries
        if do_hide_chatty_logging and app_logger.getEffectiveLevel() <= logging.INFO:
            safrs.log.setLevel(logging.WARN)  # notset 0, debug 10, info 20, warn 30, error 40, critical 50
            db_logger.setLevel(logging.WARN)
            safrs_init_logger.setLevel(logging.WARN)
            authorization_logger.setLevel(logging.WARN)

        bind_dbs.bind_dbs(flask_app)

        # https://stackoverflow.com/questions/34674029/sqlalchemy-query-raises-unnecessary-warning-about-sqlite-and-decimal-how-to-spe
        warnings.simplefilter("ignore", category=sa_exc.SAWarning)  # alert - disable for safety msgs

        def constraint_handler(message: str, constraint: Constraint, logic_row: LogicRow):
            """ format LogicBank constraint exception for SAFRS """
            if constraint is not None and hasattr(constraint, 'error_attributes'):

                detail = {"model": logic_row.name, "error_attributes": constraint.error_attributes}
            else:
                detail = {"model": logic_row.name}
            raise ValidationErrorExt(message=message, detail=detail)

        admin_enabled = os.name != "nt"
        admin_enabled = False
        """ internal use, for future enhancements """
        if admin_enabled:
            flask_app.config.update(SQLALCHEMY_BINDS={'admin': 'sqlite:////tmp/4LSBE.sqlite.4'})

        db = SQLAlchemy()
        db.init_app(flask_app)
        flask_app.db = db
        with flask_app.app_context():

            with open(Path(project_path).joinpath('security/system/custom_swagger.json')) as json_file:
                custom_swagger = json.load(json_file)
            safrs_api = SAFRSAPI(flask_app, app_db= db, host=args.swagger_host, port=args.swagger_port, client_uri=args.client_uri,
                                 prefix = args.api_prefix, custom_swagger=custom_swagger)

            if os.getenv('APILOGICSERVER_ORACLE_THICK'):
                oracledb.init_oracle_client(lib_dir=os.getenv('APILOGICSERVER_ORACLE_THICK'))

            db = safrs.DB  # valid only after is initialized, above
            session: Session = db.session

            if admin_enabled:  # unused (internal dev use)
                db.create_all()
                db.create_all(bind='admin')
                session.commit()

            from api import expose_api_models, customize_api

            import database.models
            app_logger.info("Data Model Loaded, customizing...")
            from database import customize_models

            activate_logicbank(session, constraint_handler)
            
            method_decorators : list = []
            safrs_init_logger.setLevel(logging.WARN)
            expose_api_models.expose_models(safrs_api, method_decorators)
            app_logger.info(f'Declare   API - api/expose_api_models, endpoint for each table on {args.swagger_host}:{args.swagger_port}, customizing...')
            customize_api.expose_services(flask_app, safrs_api, project_dir, swagger_host=args.swagger_host, PORT=args.port)  # custom services

            if args.security_enabled:
                configure_auth(flask_app, database, method_decorators)

            if args.security_enabled:
                from security import declare_security  # activate security
                app_logger.info("..declare security - security/declare_security.py"
                    # not accurate: + f' -- {len(database.database_discovery.authentication_models.metadata.tables)}'
                    + ' authentication tables loaded')
                declare_security_message = declare_security.declare_security_message

            from api.system.opt_locking import opt_locking
            from config.config import OptLocking
            if args.opt_locking == OptLocking.IGNORED.value:
                app_logger.info("\nOptimistic Locking: ignored")
            else:
                opt_locking.opt_locking_setup(session)

            kafka_producer.kafka_producer()
            kafka_consumer.kafka_consumer(safrs_api = safrs_api)

            n8n_producer.n8n_producer()

            SAFRSBase._s_auto_commit = False
            session.close()
        
        safrs.log.setLevel(safrs_log_level)
        db_logger.setLevel(db_log_level)
        authorization_logger.setLevel(authorization_log_level)

        if os.getenv('APILOGICPROJECT_DEBUG'):  # temp debug since logging in config is not happening
            KAFKA_SERVER = os.getenv('KAFKA_SERVER')
            is_empty = False
            if KAFKA_SERVER is not None:
                is_empty = KAFKA_SERVER == ""
            is_none = KAFKA_SERVER is None
            app_logger.debug(f'\nDEBUG KAFKA_SERVER: [{KAFKA_SERVER}] (is_empty: {is_empty}) (is_none: {is_none}) \n')
            app_logger.debug(f'... Args.instance.kafka_producer: {Args.instance.kafka_producer}\n')


