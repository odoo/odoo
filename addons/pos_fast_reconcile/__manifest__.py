# -*- coding: utf-8 -*-
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT
# SHALL THE COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE
# FOR ANY DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

{
    'name': 'Point of Sale - Fast Reconcile',
    'version': '1.1',
    'category': 'Point Of Sale',
    'author': 'Odoo Support',
    'sequence': 20,
    'summary': 'Performance patch for the Point of Sale',
    'description': """
Performance Patch for v11.0
===========================

For POS Sessions over several hundreds orders, the closing can take an extremely
long time, mainly for 2 reasons:

- The reconciliation is O(n²), which means that reconciling the move lines of
  the payments with the move lines of the session gets longer fast
- The creation of move lines for each payment takes a long time

For the `master` branch, we are currently developping a batch create mechanism
in the ORM that should allow for the creation of a big amount of move lines
without intermediary recomputes (among other things).

The reconciliation algorithm has already been merged in master and is now
O(n log(n)), which should improve performance for these cases significantly.

This being a stable branch, we do not have the luxury of merging this. Instead,
Odoo Support provides this 'fix module' for those that are interested.

In a nutshell:

- Hardcoded fast creation of move lines for payments
    Note that this bit could potentially be incompatible with custom modules that
    modify the schema for the account_move_line table
- Fast Reconcile Algorithm
    Only applied to the reconciliation of the POS Sessions move lines and *not*
    applied to the rest of the accounting mechanisms.

Note that this module is provided outside of the standard Odoo code and is not
covered by any warranty. See the disclaimer in the manifest of this module
for more information.
    """,
    'depends': ['point_of_sale'],
    'installable': True,
    'website': 'https://www.odoo.com/help',
}
