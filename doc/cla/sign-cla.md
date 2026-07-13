# Sign the Odoo CLA

In order for your contribution to Odoo to be accepted, you have to sign the
Odoo Contributor License Agreement (CLA). More information about this
requirement is explained in the [FAQ](#faq).

## If you are an individual

1.  Read the [Individual Contributor License Agreement](icla-1.0.md)

2.  Modify your current pull request, or make a new pull request on
    [odoo/odoo](https://github.com/odoo/odoo), adding a new file
    `<lowercase-github-login>.md` under the [`doc/cla/individual`](individual/) directory.
    If your GitHub login is `ODony`, the file would be
    `doc/cla/individual/odony.md`. The file should contain:

```
<country>, <date>

I hereby agree to the terms of the Odoo Individual Contributor License
Agreement v1.0.

I declare that I am authorized and able to make this agreement and sign this
declaration.

Signed,

<name> <git_email> https://github.com/<login>
```

    Replacing the following placeholders:

    * `<country>`: your country
    * `<date>`: current date in the form `YYYY-MM-DD`
    * `<name>`: your name
    * `<git_email>`: your git committer email **(use `git config user.email` to see it)**
    * `<login>`: your GitHub login

3. An Odoo R&D Team member will verify and accept your Pull Request. You can
make other pull requests, but we won't be able to merge them until your CLA
signature is merged.

## If you work for a company

1.  Read the [Corporate Contributor License Agreement](ccla-1.0.md)

2.  Modify your current pull request, or make a new pull request on
    [odoo/odoo](/odoo/odoo), adding a new file `<lowercase-company-name>.md`
    under the [`doc/cla/corporate`](corporate/) directory.
    If the name of the company is Odoo, the file would be
    `doc/cla/corporate/odoo.md`. The file should contain:

```
<country>, <date>

<company-name> agrees to the terms of the Odoo Corporate Contributor License
Agreement v1.0.

I declare that I am authorized and able to make this agreement and sign this
declaration.

Signed,

<name> <git_email> https://github.com/<login>

List of contributors:

<name> <git_email> https://github.com/<login>
```

    The List of contributors should list the individual contributors working
    for the company.

    Replacing the following placeholders:

    * `<country>`: your country
    * `<date>`: current date in the form `YYYY-MM-DD`
    * `<name>`: your name
    * `<git_email>`: git committer email **(use `git config user.email` to see it)**
    * `<login>`: your GitHub login

3. An Odoo R&D Team member will verify and accept your Pull Request. You can
make other pull requests, but we won't be able to merge them until your CLA
signature is merged.

## If you don't have a github account

If you cannot submit your signature using a pull request, you may alternatively
print the CLA, complete it, sign it, scan it and send it by email to
`cla-submission` `at` `odoo.com`.  In that case someone from the Odoo team will
make the pull request on your behalf.

* Printable Odoo CCLA v1.0 https://www.odoo.com/files/legal/Odoo-CCLA-v1.0.pdf
* Printable Odoo ICLA v1.0 https://www.odoo.com/files/legal/Odoo-ICLA-v1.0.pdf

# FAQ

## Why do I need to accept a CLA ?

The goal of having a Contributor License Agreement for Odoo is to:

* clearly define the terms under which intellectual property (patches, pull
  requests, etc.) have been contributed to the Odoo project

* protect the Odoo project and its users in case of legal dispute about the
  origin or ownership of any part of the code

* protect the Odoo project and its users from bad actors who would contribute
  and then try to withdraw their contributions or cause legal trouble, e.g. in
  the form of patent lawsuits

This is done by establishing a credible, non-repudiable record that each
contributor really intended to contribute to the Odoo project under specific
terms, and they had the right to make those contributions.

The CLA is for the protection of the contributors, the project and its users.
It does not change your rights to use your own contributions for any other
purpose.

The Odoo CLA is based on the Apache Software Foundation CLA v2.0, as
can be found on the Apache website.

This CLA is not a copyright assignment, it is a pure license agreement. You
keep the full copyright for your contributions, you simply provide an
irrevocable license to the project maintainer, Odoo S.A. to use, modify and
distribute your contributions without further restrictions.

## How does it work?

Each individual contributor (making contributions only on their own behalf) is
required to sign and submit the Individual Contributor License Agreement
(ICLA) of Odoo.  The agreement is executed by adding your name and
signature to the list of validated contributors inside the project source code.

If someone is unable to sign the CLA, their contributions will have to be
removed from the Odoo project.

In addition, if some or all of someone's contributions are written as part of
an employment by somebody else, the work may not belong to the contributor but
to their employer, depending on the contract terms and local laws. In that case
the employer needs to sign the Corporate Contributor License Agreement (CCLA),
including the names of all contributors allowed to make those contributions in
order for those contributions to be accepted.

The contributors should still sign the Individual CLA, in order to cover the
contributions that do not belong to the employer.

Contributors who have signed the ICLA without a CCLA from their employer should
be very careful.

The ICLA (section 4) is a legal declaration where the contributor states they
have the right to make the contributions. These contributors should only
submit contributions they are really entitled to license.

