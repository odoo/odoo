Contributing to Odoo
====================

Reporting Issues
----------------
If possible, always attach a pull request when creating an issue (GitHub will automatically create an issue when submiting the changes). The issues not linked to a pull request or an internal ticket on odoo.com will be handled with a lower priority.
If later on you create a pull request solving an opened issue, do not forget to reference to it in your pull request (e.g.: "This patch fixes issue #42").

Which version should I submit to?
---------------------------------
Periodically, we forward port the fixes realised in the latest stable version to master and intermediate saas repositories. This means that you should submit your pull request against the lowest supported version. If applying, you should always submit your code against `odoo/7.0`. The `saas-x` versions are intermediate versions 

![Submiting against the right version](/doc/_static/pull-request-version.png)

However your change **must** be submited against `odoo/master` if

* it modifies the database structure (e.g.: adding a new field)
* it adds a new feature

Why was my fix is set as blocked?
---------------------------------
The label *blocked* is used when an action is required from the submiter. The typical reasons are:

* the fix is incomplete/incorrect and a change is required
* more information is required

Pull requests with the blocked label will not be processed as long as the label remains. Once the correction done, we will review it and eventually remove the label.

Why was my issue closed without merging?
----------------------------------------
A pull request is closed when it will not be merged into odoo. The typical reasons are:

* the fix/issue is invalid (label *wontfix*)
* the fix/issue is a duplicated of another opened issue
* the pull request should be resubmited against another version
