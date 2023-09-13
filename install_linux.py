import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Callable

import click
import coloredlogs
import inquirer3
from plumbum import local, ProcessExecutionError
from plumbum.commands.base import BoundCommand

coloredlogs.install(level=logging.DEBUG)

DEV_PATH = Path('~/dev').expanduser()

python3 = local[sys.executable]
sudo = local['sudo']
killall = local['killall']
git = local['git']
cp = local['cp']

# make sure local installations are in user's PATH
os.environ['PATH'] += ':' + str(Path('~/.local/bin').expanduser())

logger = logging.getLogger(__name__)

AUTOMATION_MODE = False


def confirm_install(component: str, installer: Callable):
    if AUTOMATION_MODE or inquirer3.confirm(f'To {component}?', default=False, show_default=True):
        installer()


def insert_number_install(message: str, installer: BoundCommand, default_number: int):
    installer[default_number if AUTOMATION_MODE else inquirer3.text(message, default=default_number)]()


def git_clone(repo_url: str, branch='master'):
    try:
        git('clone', '--recurse-submodules', '-b', branch, repo_url)
    except ProcessExecutionError as e:
        if 'already exists and is not an empty directory' not in e.stderr:
            raise
        cwd = os.getcwd()
        os.chdir(repo_url.rsplit('/', 1)[1].rsplit('.git', 1)[0])
        try:
            git('pull', 'origin', branch)
        except ProcessExecutionError as e:
            if ('Please commit your' not in e.stderr) and ('You have unstaged' not in e.stderr) and (
                    'Need to specify' not in e.stderr):
                raise
            logger.warning(f'failed to pull {repo_url}')
        os.chdir(cwd)


def install_apt_packages():
    logger.info('installing apt packages')

    packages = ['git', 'git-lfs', 'cmake', 'openssl', 'bat', 'fzf', 'wget', 'htop', 'curl', 'ncdu', 'watch',
                'bash-completion', 'ripgrep', 'python-tk', 'nodejs', 'jq', 'tldr']

    sudo('apt', 'update')

    for package in packages:
        confirm_install(f'install {package}', sudo['apt', 'install', '--yes', package])


def install_python_packages():
    logger.info('installing python packages')

    confirm_install('upgrade pip', python3['-m', 'pip', 'install', '-U', 'pip'])

    python_packages = ['xattr', 'pyfzf', 'artifactory', 'humanfriendly', 'pygments', 'ipython', 'plumbum',
                       'pymobiledevice3', 'harlogger', 'cfprefsmon', 'pychangelog2']

    for package in python_packages:
        confirm_install(f'install {package}', python3['-m', 'pip', 'install', '-U', package])


def install_xonsh():
    logger.info('installing xonsh')

    confirm_install('upgrade pip', python3['-m', 'pip', 'install', '-U', 'pip'])

    python3('-m', 'pip', 'install', '-U', 'xonsh')

    confirm_install(f'install xonsh attributes', python3['-m', 'pip', 'install', '-U', 'xontrib-argcomplete',
    'xontrib-fzf-widgets', 'xontrib-z', 'xontrib-up', 'xontrib-vox', 'xontrib-jedi'])

    xonsh_path = shutil.which('xonsh')
    if xonsh_path not in open('/etc/shells', 'r').read():
        sudo('sh', '-c', f'echo {xonsh_path} >> /etc/shells')

    confirm_install('install/reinstall fzf', sudo['apt', 'install', '--yes', 'fzf'])
    confirm_install('install/reinstall bash-completion', sudo['apt', 'install', '--yes', 'bash-completion'])

    def change_shell() -> None:
        os.system(f'chsh -s {xonsh_path}')

    confirm_install('set xonsh to be the default shell', change_shell)

    def set_xonshrc():
        DEV_PATH.mkdir(parents=True, exist_ok=True)

        os.chdir(DEV_PATH)
        git_clone('git@github.com:doronz88/linuxsetup.git', 'main')
        cp('worksetup/.xonshrc', Path('~/').expanduser())

    confirm_install('set ready-made .xonshrc file', set_xonshrc)


def set_automation(ctx, param, value):
    if value:
        global AUTOMATION_MODE
        AUTOMATION_MODE = True


class BaseCommand(click.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params[:0] = [
            click.Option(('-a', '--automated'), is_flag=True, callback=set_automation, expose_value=False,
                         help='do everything without prompting (unless certain removals are required)')]


@click.group()
def cli():
    """ Automate selected installs """
    pass


@cli.command('apt-packages', cls=BaseCommand)
def cli_apt_packages():
    """ Install selected apt packages """
    install_apt_packages()


@cli.command('python-packages', cls=BaseCommand)
def cli_python_packages():
    """ Install selected python packages """
    install_python_packages()


@cli.command('xonsh', cls=BaseCommand)
def cli_xonsh():
    """ Install xonsh """
    install_xonsh()


@cli.command('everything', cls=BaseCommand)
def cli_everything():
    """ Install everything """
    install_apt_packages()
    install_python_packages()
    install_xonsh()


if __name__ == '__main__':
    cli()
