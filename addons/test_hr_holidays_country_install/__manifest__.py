{
    'name': 'Time Off: company country set by module data (reproducer)',
    'version': '1.0',
    'category': 'Hidden/Tests',
    'author': 'Vauxoo',
    'description': """
Minimal reproducer for the ``_check_country_change_holidays`` constraint
aborting a module installation.

Installing this module on a clean database raises::

    odoo.exceptions.ValidationError: The company country cannot be changed
    while time off leaves or allocations with the country exist.

The three data files reproduce, in a single module, the ordering that any
real database hits across several modules:

1. ``00_company_country_initial.xml`` gives the company a country, the way a
   localization or a company-setup module does.
2. ``01_time_off_records.xml`` creates a time off type and an allocation, the
   way ``hr_holidays`` demo data does. ``hr.leave.type.country_id`` is a
   stored compute that captures the company country at creation time, so the
   type is pinned to the country of step 1.
3. ``02_company_country_final.xml`` moves the company to another country, the
   way a downstream localization module does. This is the write the
   constraint rejects.

No step here is a user action: all three are ORM writes performed by the data
loader, under ``install_mode``. The constraint cannot be satisfied by
reordering, because in a real database the records it objects to belong to a
module that is a *dependency* of the one being installed.

To reproduce::

    createdb repro
    ./odoo-bin -d repro -i test_hr_holidays_country_install --stop-after-init

Demo data is off by default in 19.0 and is not needed: the module brings its
own conflicting records. In a real database they come from ``hr_holidays``
demo data instead, which is why the failure shows up on clean CI builds.

No test can cover this: ``_check_country_change_holidays`` returns early on
``tools.config['test_enable'] or modules.module.current_test``, and one of the
two is set for every test run, so the constraint never reaches its body from a
test.

Not meant for merge. See odoo/odoo#279210 for the proposed fix.
""",
    'depends': ['hr_holidays'],
    'data': [
        'data/00_company_country_initial.xml',
        'data/01_time_off_records.xml',
        'data/02_company_country_final.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
