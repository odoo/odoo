#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

from pathlib import Path

if os.geteuid() == 0:
    raise Exception("This script should not be run as root")

base_dir = Path.home() / 'src' / 'master'
# note, repositories are automaticaly set in a master directory to allow an easy setup of multiverse later

parser = argparse.ArgumentParser()
parser.add_argument("--dryrun", help="Only log install commands, don't execute them", action='store_true')
# install without asking
parser.add_argument("--interactive", "-i", help="Interactive install, ask before each option", action='store_true')
parser.add_argument("-y", help="Yes to all, don't ask anything", action='store_true')
# install without asking
parser.add_argument("-a", help="Propose/install everything", action='store_true')
parser.add_argument("-v", "--verbose", help="Verbose mode", action='store_true')

features_group = parser.add_argument_group('Features group selection')
features_group.add_argument("--nodefault", '-n', help="Don't install default set", action='store_true')
features_group.add_argument("--dev", "-d", help="Install additional dev tools and add dev remotes (chrome, ruff, ..)", action='store_true')
features_group.add_argument("--opt", "-o", help="Install additional optional dependencies (gevent, wkhtml, ebaysdk, ...)", action='store_true')
features_group.add_argument("--docker", help="Install docker and build a ready to used docker image", action='store_true')

individual_features = parser.add_argument_group('Individual feature selection')
individual_features.add_argument("--git-clone", help="Clone odoo git repository (enabled by default)", action='store_true')
individual_features.add_argument("--postgres", help="Install postgres (enabled by default)", action='store_true')
individual_features.add_argument("--minimal-packages", help="Install packages needed to run odoo core (enabled by default)", action='store_true')
individual_features.add_argument("--default-packages", help="Install default packages needed by some community modules (enabled by default) (implies base-packages)", action='store_true')
individual_features.add_argument("--dev-packages", help="Install dev packages (enabled by dev)", action='store_true')
individual_features.add_argument("--dev-remote", help="Add git dev remotes (enabled by dev)", action='store_true')
individual_features.add_argument("--dev-repos", help="Add documentation and upgrade-utils repos (enabled by dev)", action='store_true')
individual_features.add_argument("--chrome", '-c', help="Install chrome latest (enabled by dev)", action='store_true')
individual_features.add_argument("--pdf", '-w', help="Install wkhtmltopdf -- qt patched -- (enabled by opt)", action='store_true')
individual_features.add_argument("--opt-packages", help="Install optional packages, for multiworker, enterprise and other advanced features (enabled by opt)", action='store_true')
individual_features.add_argument("--rtlcss", help="Install rtlcss (enabled by opt)", action='store_true')

configuration = parser.add_argument_group('Configuration')
configuration.add_argument("--src-dir", help=f"Place where source should be clone, default to {base_dir}", default=base_dir)
configuration.add_argument("--git-use-ssh", help=f"Place where source should be clone, default to {base_dir}", action='store_true')
configuration.add_argument("--branch", help=f"Branch to checkout after clone")

args = parser.parse_args()
args.default = True

if args.nodefault:
    args.default = False
    if args.a:
        raise Exception("Can't use -a and --nodefault at the same time")

## disable default if a specific default option is selected
#if args.postgres or args.git_clone or args.default_packages or args.minimal_packages:
#    # if manually selecting a default option, disable other option
#    args.default = False

# option implications
if args.a:
    args.dev = True
    args.opt = True
if args.default:
    args.git_clone = True
    args.postgres = True
    args.minimal_packages = True
    args.default_packages = True
if args.dev:
    args.dev_packages = True
    args.dev_remote = True
    args.dev_repos = True
    args.chrome = True
if args.opt:
    args.opt_packages = True
    args.pdf = True
    args.rtlcss = True

# prototype example of using click for interactive mode, to remove if overkill
if args.interactive:
    try:
        from pick import Picker
    except ModuleNotFoundError:
        input("pick is required for interactive mode and will be installed, press enter to continue")
        subprocess.run('pip install --break-system-package pick', shell=True)
        import importlib
        import site
        importlib.reload(site)
        from pick import Picker

    title = 'Please choose the component you want to install/setup. Press [Enter] to continue'
    options = [
        "git_clone",
        "postgres",
        "minimal_packages",
        "default_packages",
        "dev_packages",
        "dev_remote",
        "dev_repos",
        "chrome",
        "opt_packages",
        "pdf",
        "rtlcss",
    ]
    actions = [action for action in parser._actions if action.dest in options]
    options_names = [action.help.split('(')[0] for action in actions]
    selected_indexes = [index for index, action in enumerate(actions) if getattr(args, action.dest)]
    picker = Picker(options_names, title, multiselect=True, min_selection_count=1)
    picker.selected_indexes = selected_indexes
    selected = picker.start()
    selected_index = [s[1] for s in selected]
    for index, action in enumerate(actions):
        option = action.dest
        setattr(args, option, index in selected_index)
    args.interactive = False

base_dir = Path(args.src_dir)
odoo_dir = base_dir / 'odoo'
if not odoo_dir.is_dir() and not args.git_clone and args.docker:
    raise Exception(f"Odoo directory not found, enable git_clone or clone odoo repository manually in {odoo_dir} or specify a valid src-dir")

commands_to_execute = []
commands_summaries = []

# CONFIGURATIONS

if args.git_use_ssh:
    git_base = 'git@github.com:'
    suffix = '.git'
else:
    git_base = 'https://github.com/'
    suffix = ''

# clone_params = '--filter=tree:0'
clone_params = '--filter=blob:none'
# --filter=tree:0 could be another faster option but is less practical on usage for blames


def main():
    has_git = is_installed('git')
    if args.git_clone and ask("Clone odoo repositories %s" % ('' if has_git else "and install git")):
        def clone(repo):
            repo_dir = base_dir / 'odoo'
            if not repo_dir.is_dir():
                run(f'git -C {base_dir} clone {clone_params} {git_base}odoo/{repo}{suffix}')
            else:
                print(f"{repo} repo already cloned")

            if args.dev_remote and ask("Add odoo-dev remote"):
                # add dev remote
                run(f'(git -C {odoo_dir} remote | grep dev) || git -C {odoo_dir} remote add dev {git_base}odoo-dev/odoo{suffix}')
            if args.branch and ask(f"Checkout `{args.branch}` branch"):
                run(f'((git -C {repo_dir} fetch origin {args.branch} || git -C {repo_dir} fetch dev {args.branch}) && git -C {repo_dir} checkout {args.branch}) || echo "Was not able to checkout branch {args.branch}, skipping"')


        # TODO write config file for srcdir
        if not has_git:
            run('sudo apt-get install git')
        if not base_dir.is_dir():
            run('mkdir -p %s' % base_dir)
        clone('odoo')

        if args.dev_repos and ask("Clone documentation and upgrade-util repositories"):
            clone('documentation')
            clone('upgrade-util')
        # note: this won't work if a github user is not setup, should we fallback on https?

    if args.postgres:
        if is_installed('postgresql-common'):
            if args.verbose:
                print("Postgres installation detected, skipping install")
        else:
            if ask("Install potgress"):
                run('sudo apt-get install postgresql postgresql-client')
                run('sudo service postgresql start')
        if ask("Create the potgresql user"):
            check_user_exist = r'(psql postgres -c "\l" > /dev/null)'
            create_user = '(sudo -u postgres createuser -d -R -S $(whoami) && createdb $(whoami))'
            run(f'{check_user_exist} || {create_user}')

    if args.docker and ask("Install docker"):
        if not is_installed('docker'):
            run('sudo apt-get install docker.io')
        run('sudo service docker start')
        run('sudo groupadd docker || echo "group docker already exists, skipping"')

        # TODO this following part may actually be moved to a more apropriate tooling in odoo/dev/tools
        run(f'{odoo_dir}/setup/autoinstall/docker/build')

    if args.minimal_packages and ask("Install minimal debian packages (odoo core)"):
        run(f'sudo apt-get install --no-install-recommends {base_packages}')
        if args.default_packages and ask("Install default dependencies debian packages (modules)"):
            run(f'sudo apt-get install --no-install-recommends {default_packages}')

    if args.dev_packages and ask("Install dev dependencies"):
        run(f'sudo apt-get install --no-install-recommends {dev_packages}')
        run(f'pip install --break-system-packages {dev_pip_packages}')
        if not is_installed('npm'):
            run('sudo apt-get install --no-install-recommends npm')
        run('NODE_PATH=/usr/lib/node_modules/')
        run('export NODE_PATH=/usr/lib/node_modules/')
        run('export npm_config_prefix=/usr')
        run('sudo npm install --force -g es-check@6.0.0 eslint@8.1.0 prettier@2.7.1 eslint-config-prettier@8.5.0 eslint-plugin-prettier@4.2.1')

    if args.opt and ask("Install optional debian packages"):
        run(f'sudo apt-get install --no-install-recommends {opt_packages}')
        run(f'pip install --break-system-packages {opt_pip_packages}')

    missing_chrome = not is_installed('google-chrome-*') and not is_installed('chromium')
    if missing_chrome and args.chrome and ask("Install chrome"):
        # TODO user repositories
        chrome_url = 'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'
        y = "-y" if not args.interactive else ''
        run(f"""curl -sSL {chrome_url} -o /tmp/chrome.deb \
            && sudo apt-get {y} install --no-install-recommends /tmp/chrome.deb \
            && rm /tmp/chrome.deb
            """)

    missing_wkhtml = not is_installed('wkhtmlto*')
    if missing_wkhtml and args.pdf and ask("Install wkhtmltopdf"):
        version = "0.12.6.1-2"
        distro = "jammy"  # todo make dynamic for debian
        run(f'curl -sSL https://github.com/wkhtmltopdf/packaging/releases/download/{version}/wkhtmltox_{version}.{distro}_amd64.deb -o /tmp/wkhtml.deb \
            && sudo apt-get -y install --no-install-recommends --fix-missing -qq /tmp/wkhtml.deb \
            && rm /tmp/wkhtml.deb')

    missing_rtlcss = subprocess.run('rtlcss --version > /dev/null 2>&1', shell=True).returncode != 0
    if missing_rtlcss and args.rtlcss and ask("Install node"):
        if not is_installed('npm'):
            run('sudo apt-get install --no-install-recommends npm')
        run('export NODE_PATH=/usr/lib/node_modules/')
        run('export npm_config_prefix=/usr')
        # todo check if root and force is necessary
        run('sudo npm install --force -g rtlcss@3.4.0')

    if to_confirm:
        print("The script will:")
        for c in to_confirm:
            print('\t', '-', c)
        if not args.y:
            while res := input("Press enter to continue, type 'exit' to abort:"):
                if res == 'exit':
                    sys.exit(1)

    for command in commands_to_execute:
        if args.dryrun:
            print(command)
        else:
            execute(command)


# START DEPS
base_packages = ' '.join([  # noqa: FLY002
    'python3-decorator',
    'python3-dateutil',
    'python3-babel',  # locale
    'python3-idna',  # domain encoding for mail server rfc5890 (could be make optionnal)
    'python3-passlib',  # password hashing and totp
    'python3-pil',  # image resize
    'python3-psutil',  # server.py memory_info
    'python3-reportlab',  # tools for pdf banners, qrcode, ... (could be make optionnal)
    'python3-requests',  # gravatar, database load, webhook, ... (could be make optionnal)
    '"python3-lxml-html-clean|python3-lxml"',  # data files and views
    'python3-openssl',  # mail server connect
    'python3-polib',  # to import tranlsations (could be make optionnal)
    'python3-psycopg2',
    '"python3-pypdf2|python3-pypdf"',  # OdooPdfFileWriter and others, (could be make optionnal)
    'python3-werkzeug',
    'python3-zeep',  # mainly for l10n and enterprise, (could be make optionnal)
    'python3-rjsmin',  # js assets bundle generation
    'python3-docutils',  # ir_module get_desc fallback, could be removed maybe
    # unsure for vobject 5
    #  num2words, logging warning if not installed but not needed to install
])
default_packages = ' '.join([  # noqa: FLY002
    'adduser',
    'postgresql-client'
    '"fonts-dejavu-core|fonts-freefont-ttf|fonts-freefont-otf|fonts-noto-core" fonts-inconsolata fonts-font-awesome fonts-roboto-unhinted gsfonts',
    'libjs-underscore lsb-base',
    'python3-asn1crypto python3-cbor2',
    'python3-chardet python3-dateutil python3-decorator python3-freezegun python3-geoip2 python3-jinja2',
    'python3-libsass python3-num2words python3-ofxparse python3-openpyxl',
    'python3-polib python3-psutil "python3-pypdf2|python3-pypdf" python3-qrcode',
    'python3-renderpm python3-stdnum python3-tz python3-vobject python3-werkzeug python3-xlsxwriter',
    'python3-xlrd',
])
dev_packages = 'pylint python3-ipython python3-pudb'
# flake8 python3-dev python3-mock
dev_pip_packages = 'ruff==0.4.7'

opt_packages = ' '.join([  # noqa: FLY002
    'python3-gevent',  # multiworker
    'python3-websocket',  # bus, looks mandatory (WTF? installed by another one?)
    #'publicsuffix',
    'python3-dbfread',  # enterprise
    'python3-markdown',  # upgrade util
    'python3-phonenumbers',  # phone_validation, enterprise, ... # TODO check why not in default_packages
    'python3-google-auth',  # cloud storage, enterprise
    # 'libpq-dev', # unsure, related to psycopg2
    'python3-jwt',  # enterprise
    'python3-html2text',  # i
    # 'python3-suds', # unsure, alternative to zeep
    'python3-xmlsec',  # enterprise
])
# apt-transport-https build-essential ca-certificates curl file fonts-freefont-ttf fonts-noto-cjk gawk gnupg gsfonts libldap2-dev libjpeg9-dev libsasl2-dev libxslt1-dev lsb-release npm ocrmypdf sed sudo unzip xfonts-75dpi zip zlib1g-dev
opt_pip_packages = 'ebaysdk==2.1.5 pdf417gen==0.7.1'
# END DEPS



def run(command):
    if not args.interactive and ('install' in command and 'apt' in command and not '-y' in command):
        command = command + " -y"
    if 'apt' in command and 'install' in command and not run.updated:
        run.updated = True
        commands_to_execute.append('sudo apt-get update')
    commands_to_execute.append(command)


run.updated = False


def execute(command):
    print('>', command)
    res = subprocess.run(command, shell=True)
    if res.returncode != 0:
        sys.exit(res.returncode)

def ask(message):
    commands_summaries.append(message)
    return True


def install_package(*packages):
    run("sudo apt-get install " + " ".join(packages))


def is_installed(package):
    try:
        subprocess.check_output(f"dpkg -l {package} | grep -E '^ii'", shell=True, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

main()
