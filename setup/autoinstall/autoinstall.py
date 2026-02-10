#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path

if os.geteuid() == 0:
    raise Exception("This script should not be run as root")

user_name = os.getenv('USER')

# TODO write config file for srcdir

base_dir = Path.home() / 'src' / 'master'
# note, repositories are automaticaly set in a master directory to allow an easy setup of multiverse later

parser = argparse.ArgumentParser()
parser.set_defaults(disable_default_set=False)
parser.add_argument("--dry-run", help="Only log install commands, don't execute them", action='store_true')
# install without asking
parser.add_argument("--interactive", "-i", help="Interactive install, ask before each option", action='store_true')
parser.add_argument("-y", help="Yes to all, don't ask anything", action='store_true')
# install without asking
parser.add_argument("-a", help="Propose/install everything", action='store_true')
parser.add_argument("-v", "--verbose", help="Verbose mode", action='store_true')


class strore_true_no_default(argparse.Action):
    def __init__(self, nargs=0, **kw):
        super().__init__(nargs=nargs, **kw)

    def __call__(self, parser, args, values, option_string=None):
        setattr(args, self.dest, True)
        args.disable_default_set = True


features_group = parser.add_argument_group('Features group selection')
features_group.add_argument("--default", help="Don't install default set", action='store_true')
features_group.add_argument("--dev", "-d", help="Install additional dev tools and add dev remotes (chrome, ruff, ..)", action=strore_true_no_default)
features_group.add_argument("--opt", "-o", help="Install additional optional dependencies (gevent, wkhtml, ebaysdk, ...)", action=strore_true_no_default)
features_group.add_argument("--docker", help="Install docker and build a ready to used docker image. Implies --odoo-repo if odoo sources are missing", action=strore_true_no_default)

individual_features = parser.add_argument_group('Individual feature selection')
individual_features.add_argument("--odoo-repo", help="Clone odoo git repository. Will install git if missing. (enabled by default)", action=strore_true_no_default)
individual_features.add_argument("--private-repo", "-e", help="Clone enterprise and upgrade git repository. Will install git if missing. (enabled by default)", action=strore_true_no_default)
individual_features.add_argument("--postgres", help="Install postgres (enabled by default)", action=strore_true_no_default)
individual_features.add_argument("--minimal-packages", help="Install packages needed to run odoo core (enabled by default)", action=strore_true_no_default)
individual_features.add_argument("--default-packages", help="Install default packages needed by some community modules (enabled by default) (implies base-packages)", action=strore_true_no_default)
individual_features.add_argument("--dev-packages", help="Install dev packages (enabled by dev)", action=strore_true_no_default)
individual_features.add_argument("--dev-remote", help="Add git dev remotes (enabled by dev)", action=strore_true_no_default)
individual_features.add_argument("--dev-repos", help="Add documentation and upgrade-utils repos (enabled by dev)", action=strore_true_no_default)
individual_features.add_argument("--chrome", '-c', help="Install chrome latest (enabled by dev)", action=strore_true_no_default)
individual_features.add_argument("--pdf", '-w', help="Install wkhtmltopdf -- qt patched -- (enabled by opt)", action=strore_true_no_default)
individual_features.add_argument("--opt-packages", help="Install optional packages, for multiworker, and other advanced features (enabled by opt)", action=strore_true_no_default)
individual_features.add_argument("--rtlcss", help="Install rtlcss (enabled by opt)", action=strore_true_no_default)

configuration = parser.add_argument_group('Configuration')
configuration.add_argument("--src-dir", help=f"Place where source should be clone, default to {base_dir}", default=base_dir)
configuration.add_argument("--git-use-http", help=f"Use HTTP instead of SSH for git operations", action='store_true')
configuration.add_argument("--branch", help="Branch to checkout after clone")


args = parser.parse_args()

base_dir = Path(args.src_dir)
odoo_dir = base_dir / 'odoo'

if not args.disable_default_set:
    args.default = True

# option implications
if args.a:
    args.default = True
    args.dev = True
    args.opt = True

if args.dev:
    args.dev_packages = True
    args.dev_remote = True
    args.dev_repos = True
    args.chrome = True

if args.opt:
    args.opt_packages = True
    args.pdf = True
    args.rtlcss = True

if args.default:
    args.odoo_repo = True
    args.postgres = True
    args.minimal_packages = True
    args.default_packages = True

if args.docker and not args.odoo_repo and not odoo_dir.is_dir():
    args.odoo_repo = True


if not args.odoo_repo and not odoo_dir.is_dir():
    print("WARNING: the currently selected options won't clone odoo but no odoo source dir was found. You may want to enable --default, --odoo-repo or specify --src-dir to solve this issue")

commands_summaries = []

# CONFIGURATIONS

if args.git_use_http:
    git_base_url = 'https://github.com/'
    suffix = ''
else:
    git_base_url = 'git@github.com:'
    suffix = '.git'

# clone_params = '--filter=tree:0'
clone_params = '--filter=blob:none'
# --filter=tree:0 could be another faster option but is less practical on usage for blames


def clone(repo, org='odoo'):
    check_repo_exist = f'git -C {base_dir / repo} status > /dev/null 2>&1'
    clone = f'git -C {base_dir} clone {clone_params} {git_base_url}{org}/{repo}{suffix}'
    return f'{check_repo_exist} || {clone}'


def install(*packages):
    return 'sudo DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends ' + ' '.join(packages)


def is_installed(package):
    try:
        subprocess.check_output(f"dpkg -l {package} | grep -E '^ii'", shell=True, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

class Operation:
    operations = []
    def __init__(self, enabled, message, *commands):
        self.enabled = enabled
        self.message = message
        self.commands = commands
        Operation.operations.append(self)

    @property
    def description(operation):
        description = operation.message
        if args.verbose:
            description += '\n' + ('\n'.join(['\t \t > ' + command for command in operation.commands]))
        return description

    def __repr__(self):
        return f'Operation({self.enabled}, {self.message})'

def main():
    has_git = is_installed('git')
    has_postgres = is_installed('postgresql-common')
    has_chrome = is_installed('google-chrome-*') or is_installed('chromium')
    has_wkhtml = is_installed('wkhtmlto*')
    has_docker = is_installed('docker-buildx')
    has_rtl_css = subprocess.run('rtlcss --version > /dev/null 2>&1', shell=True).returncode != 0
    odoo_dir_exists = odoo_dir.is_dir()

    if not has_git:
        Operation(
            args.odoo_repo,
            "Install git",
            install('git'),
        )

    if not odoo_dir_exists:
        Operation(
            args.odoo_repo,
            "Clone odoo repository",
            f'mkdir -p {base_dir}',
            clone('odoo'),
        )
    else:
        print('An odoo repository was detected')

    if not odoo_dir_exists or not subprocess.run(f'git -C {odoo_dir} remote | grep dev > /dev/null 2>&1', shell=True).returncode == 0:
        Operation(
            args.dev_remote,
            "Add odoo-dev/odoo remote",
            f'git -C {odoo_dir} remote add dev {git_base_url}odoo-dev/odoo{suffix}',
        )

    if args.branch:
        Operation(
            True,
            f"Checkout `{args.branch}` branch",
            f'(git -C {odoo_dir} fetch origin {args.branch}  > /dev/null 2>&1 || git -C {odoo_dir} fetch dev {args.branch}  > /dev/null 2>&1) && git -C {odoo_dir} checkout {args.branch} || git git -C {odoo_dir} rebase',
        )

    if not (base_dir / 'documentation').is_dir():
        Operation(
            args.dev_repos,
            "Clone documentation repository",
            clone('documentation'),
        )

    if not (base_dir / 'design-theme').is_dir():
        Operation(
            args.dev_repos,
            "Clone design-theme repository",
            clone('design-theme'),
        )

    if not (base_dir / 'upgrade-util').is_dir():
        Operation(
            args.dev_repos,
            "Clone upgrade-util repository",
            clone('upgrade-util'),
        )

    if not (base_dir / 'enterprise').is_dir():
        Operation(
            args.private_repo,
            "Clone enterprise repository",
            clone('enterprise'),
        )

    if not (base_dir / 'upgrade').is_dir():
        Operation(
            args.private_repo,
            "Clone enterprise repository",
            clone('upgrade'),
        )

    if not has_postgres:
        Operation(
            args.postgres,
            "Install postgres",
            install('postgresql postgresql-client'),
            'sudo service postgresql start',
        )
    else:
        print('An install of postgres was detected')


    check_user_exist = '(psql postgres -c "\\l" > /dev/null 2>&1)'
    if subprocess.run(check_user_exist, shell=True).returncode != 0:
        Operation(
            args.postgres,
            "Create the potgresql user",
            f'(sudo -u postgres createuser -d -R -S {user_name} && createdb {user_name})',
        )

    # todo create template and add it to config

    Operation(
        args.minimal_packages,
        "Install minimal debian packages (odoo core)",
        install(base_packages),
    )
    Operation(
        args.default_packages,
        "Install default dependencies debian packages (modules)",
        install(default_packages),
    )
    Operation(
        args.dev_packages,
        "Install dev dependencies debian packages, npm packages and pip packages",
        install(dev_packages),
        f'pip3 install --break-system-packages {dev_pip_packages}',
        install('npm'),
        'NODE_PATH=/usr/lib/node_modules/',
        'export NODE_PATH=/usr/lib/node_modules/',
        'export npm_config_prefix=/usr',
        'sudo npm install --force -g es-check@6.0.0 eslint@8.1.0 prettier@2.7.1 eslint-config-prettier@8.5.0 eslint-plugin-prettier@4.2.1',
    )

    Operation(
        args.opt,
        "Install optional debian packages",
        install(opt_packages),
        f'pip3 install --break-system-packages {opt_pip_packages}',
    )

    if not has_chrome:
        chrome_url = 'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'
        Operation(
            args.chrome,
            "Install chrome",
            f'curl -sSL {chrome_url} -o /tmp/chrome.deb',
            install('/tmp/chrome.deb'),
            'rm /tmp/chrome.deb',
        )
    else:
        print('An install of chrome was detected')

    if not has_wkhtml:
        version = "0.12.6.1-2"
        distro = "jammy"  # todo make dynamic for debian
        Operation(
            args.pdf,
            "Install wkhtmltopdf",
            f'curl -sSL https://github.com/wkhtmltopdf/packaging/releases/download/{version}/wkhtmltox_{version}.{distro}_amd64.deb -o /tmp/wkhtml.deb',
            'sudo apt-get -y install --no-install-recommends --fix-missing -qq /tmp/wkhtml.deb',
            'rm /tmp/wkhtml.deb'
        )
    else:
        print('An install of wkhtml was detected')

    if has_rtl_css:
        Operation(
            args.rtlcss,
            "Install rtlcss",
            install('npm'),
            'export NODE_PATH=/usr/lib/node_modules/',
            'export npm_config_prefix=/usr',
            'sudo npm install --force -g rtlcss@3.4.0',
        )
    else:
        print('An install of rtlcss was detected')

    if not has_docker:
        install_docker = [install('docker.io', 'docker-buildx')]
    else:
        print('An install of docker was detected')
        install_docker = []

    Operation(
        args.docker,
        "Install docker, configure current user and build odoo docker image",
        *install_docker,
        'sudo service docker start',
        'sudo groupadd docker || echo "group docker already exists, skipping"',
        'sudo usermod -aG docker $USER',
        f'/bin/sh {odoo_dir}/setup/autoinstall/docker/build',
    )

    # Check if an apt update is needed before installing packages
    need_update = False
    for operation in Operation.operations:
        if operation.enabled:
            for command in operation.commands:
                if 'apt' in command and 'install' in command:
                    need_update = True
    if need_update:
        Operation(
            True,
            "Update apt",
            'sudo apt-get update',
        )
        Operation.operations = [Operation.operations[-1], *Operation.operations[:-1]]  # move update to the top

    # Interactive mode if requested, allow to enable/disable each operation individually
    if args.interactive:
        interactive_checks()

    # Summary
    print("The script will:")
    for operation in Operation.operations:
        if operation.enabled:
            print('\t', '-', operation.description)

    # Ask for confirmation
    if not args.y:
        while res := input("Press enter to continue, type 'exit' to abort:"):
            if res == 'exit':
                sys.exit(1)

    # Start the installation
    for operation in Operation.operations:
        if operation.enabled:
            for command in operation.commands:
                print('>', command)
                if not args.dry_run:
                    res = subprocess.run(command, shell=True)
                    if res.returncode != 0:
                        sys.exit(res.returncode)


def interactive_checks():
    # prototype example of using click for interactive mode, to remove if overkill
    try:
        from pick import Picker
    except ModuleNotFoundError:
        input("pick is required for interactive mode and will be installed, press enter to continue")
        subprocess.run('pip3 install --break-system-package pick', shell=True)
        import importlib
        import site
        importlib.reload(site)
        from pick import Picker

    title = 'Please choose the component you want to install/setup. Press [Enter] to continue'
    options_descriptions = [operation.message for operation in Operation.operations]
    selected_indexes = [index for index, operation in enumerate(Operation.operations) if operation.enabled]
    picker = Picker(options_descriptions, title, multiselect=True, min_selection_count=1)
    picker.selected_indexes = selected_indexes
    selected = picker.start()
    selected_index = [s[1] for s in selected]
    for index, operations in enumerate(Operation.operations):
        operations.enabled = index in selected_index


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

# NOTE: ebaysdk==2.1.5 is needed for versions <= 17.*, not present here
opt_pip_packages = 'pdf417gen==0.7.1'  # needed for ln10n_cl_edi
# END DEPS


if __name__ == '__main__':
    main()
