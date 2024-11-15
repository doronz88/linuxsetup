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
    if AUTOMATION_MODE or inquirer3.confirm(f'To {component}?', default=False):
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


def add_sublim_ppa() -> None:
    # add sublimehq to list of trusted keys
    os.system(
        'wget -qO - https://download.sublimetext.com/sublimehq-pub.gpg | gpg --dearmor | '
        'sudo tee /etc/apt/trusted.gpg.d/sublimehq-archive.gpg > /dev/null')

    # add sublime-text source
    os.system('echo "deb https://download.sublimetext.com/ apt/stable/" | '
              'sudo tee /etc/apt/sources.list.d/sublime-text.list')


def install_packages():
    logger.info('installing packages')

    confirm_install(f'install sublime-text ppa', add_sublim_ppa)

    ppas = ['ppa:ettusresearch/uhd', 'ppa:deadsnakes/ppa', 'ppa:wireshark-dev/stable']

    apt_packages = ['git', 'git-lfs', 'cmake', 'openssl', 'bat', 'fzf', 'wget', 'htop', 'curl', 'ncdu', 'watch',
                    'bash-completion', 'ripgrep', 'python-tk', 'nodejs', 'jq', 'tldr', 'vim', 'sublime-text',
                    'wireshark', 'terminator', 'net-tools', 'build-essential', 'libtool', 'libusb-dev', 'libfcl-dev',
                    'libudev-dev', 'libssl-dev', 'python2-dev', 'checkinstall', 'automake']

    snap_packages = ['pycharm-community', 'code','ipsw']

    sudo('apt', 'update')

    for ppa in ppas:
        confirm_install(f'install {ppa}', sudo['add-apt-repository', '-y', ppa])

    for package in apt_packages:
        confirm_install(f'install {package}', sudo['apt', 'install', '--yes', package])

    for package in snap_packages:
        confirm_install(f'install {package}', sudo['snap', 'install', package, '--classic'])


def install_python_packages():
    logger.info('installing python packages')

    confirm_install('upgrade pip', python3['-m', 'pip', 'install', '-U', 'pip'])

    python_packages = ['xattr', 'pyfzf', 'artifactory', 'humanfriendly', 'pygments', 'ipython', 'plumbum',
                       'pymobiledevice3', 'harlogger', 'cfprefsmon', 'pychangelog2']

    for package in python_packages:
        confirm_install(f'install {package}', python3['-m', 'pip', 'install', '-U', package])


def install_xonsh():
    logger.info('installing xonsh')

    confirm_install('upgrade pipx', python3['-m', 'pip', 'install', '-U', 'pipx'])

    pipx = local['pipx']
    pipx('install', 'xonsh', '--force')

    confirm_install(f'install xonsh xontribs', pipx['runpip', 'xonsh', 'install', '-U', 'xontrib-argcomplete',
    'xontrib-fzf-widgets', 'xontrib-zoxide', 'xontrib-vox', 'xontrib-jedi'])

    xonsh_path = shutil.which('xonsh')
    if xonsh_path not in open('/etc/shells', 'r').read():
        sudo('sh', '-c', f'echo {xonsh_path} >> /etc/shells')

    confirm_install('install/reinstall fzf', sudo['apt', 'install', '--yes', 'fzf'])
    confirm_install('install/reinstall zoxide', sudo['apt', 'install', '--yes', 'zoxide'])
    confirm_install('install/reinstall bash-completion', sudo['apt', 'install', '--yes', 'bash-completion'])

    def change_shell() -> None:
        os.system(f'chsh -s {xonsh_path}')

    confirm_install('set xonsh to be the default shell', change_shell)

    def set_xonshrc():
        DEV_PATH.mkdir(parents=True, exist_ok=True)

        os.chdir(DEV_PATH)
        git_clone('git@github.com:doronz88/linuxsetup.git', 'master')
        cp('linuxsetup/.xonshrc', Path('~/').expanduser())

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


@cli.command('packages', cls=BaseCommand)
def cli_packages():
    """ Install selected packages """
    install_packages()


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
    install_packages()
    install_python_packages()
    install_xonsh()


if __name__ == '__main__':
    cli()
