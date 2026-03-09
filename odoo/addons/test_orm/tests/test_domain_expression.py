from odoo.fields import Domain
from odoo.tests.common import TransactionCase
from odoo.tests import tagged



@tagged('at_install', '-post_install')
class TransactionExpressionCase(TransactionCase):

    def _search(self, model, domain, init_domain=Domain.TRUE, test_complement=True):
        sql = model.search(domain, order="id")
        init_domain = Domain(init_domain)
        init_search = model.search(init_domain, order="id")
        fil = init_search.filtered_domain(domain)
        self.assertEqual(sql._ids, fil._ids, f"filtered_domain do not match SQL search for domain: {domain}")
        if test_complement and domain:
            # testing complement when asked, skip trivial the case where domain is TRUE
            domain = Domain(domain)

            # test whether the result of the search and the complement are equal to the universe
            complement_domain = ~domain
            if not init_domain.is_true():
                # the init_search is not TRUE
                # first, check the complement with a single search; include inactive records for the complement
                cpl = model.with_context(active_test=False).search(complement_domain, order="id")
                uni = model.with_context(active_test=False).search(Domain.TRUE, order="id")
                self.assertEqual(sorted(sql._ids + cpl._ids), uni.ids, f"{domain} and {complement_domain} don't cover all records (search all)")
                # second, for the rest of the check, limit the serach with init_domain
                complement_domain = init_domain & complement_domain

            # general case where the universe is init_search
            cpl = self._search(
                model,
                complement_domain,
                init_domain=init_domain,
                test_complement=False,
            )
            uni = init_search
            self.assertEqual(sorted(sql._ids + cpl._ids), uni.ids, f"{domain} and {complement_domain} don't cover all records")
        return sql
