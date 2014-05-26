Contributing to Odoo
====================

Reporting Issues
----------------
If possible, always attach a pull request when creating an issue (GitHub will automatically create an issue when submitting the changes). The issues not linked to a pull request or an internal request on odoo.com will be handled with a lower priority.

If later on you create a pull request solving an opened issue, do not forget to reference to it in your pull request (e.g.: "This patch fixes issue #42").

When reporting an issue or creating a pull request, use the following structure:

> **Quantity field is ignored in a sale order**
>
> Impacted versions:
> 
>  - 7.0 and above
> 
> Steps to reproduce:
> 
>  1. create a new sale order
>  2. add a line with product 'Service', quantity 2, unit price 10.0
>  3. validate the sale order
> 
> Current behavior:
> 
>  - Total price of 10.0
> 
> Expected behavior:
> 
>  - Total price of 20.0 (2 * 10 = 20)

For web or rendering issues, do not forget to specify the operating system and browser you are using.

Against which version should I submit a patch?
----------------------------------------------
Periodically, we forward port the fixes realized in the latest stable version to master and intermediate saas repositories. This means that you should submit your pull request against the lowest supported version. If applying, you should always submit your code against `odoo/7.0`. The `saas-x` versions are intermediate versions between stable versions.

![Submiting against the right version](/doc/_static/pull-request-version.png)

However your change **must** be submitted against `odoo/master` if

* it modifies the database structure (e.g.: adding a new field)
* it adds a new feature

Why was my fix labeled as blocked?
----------------------------------
The label *blocked* is used when an action is required from the submitter. The typical reasons are:

* the fix is incomplete/incorrect and a change is required
* more information is required

Pull requests with the blocked label will not be processed as long as the label remains. Once the correction done, we will review it and eventually remove the label.

Why was my issue closed without merging?
----------------------------------------
A pull request is closed when it will not be merged into odoo. This will typically happens if the fix/issue:

* is not relevant to odoo development (label *invalid*)
* is not considered as a bug or we have no plan to change the current behavior (label *wontfix*)
* is a duplicated of another opened issue (label *duplicate*)
* the pull request should be resubmitted against another version

What is this odoo-dev repository? Should I use it?
--------------------------------------------------

The `odoo-dev/odoo` repository is an internal repository used by the R&D of Odoo to keep the main repository clean. If you are coming from Launchpad, this is the equivalent of the `~openerp-dev` repository.

When forking odoo to submit a patch, always use the `github.com/odoo/odoo` repository. Be also careful of the version you are branching as it will determine the history once the pull request will be realized (e.g.: `git checkout -b 7.0-my-branch odoo/7.0`).
