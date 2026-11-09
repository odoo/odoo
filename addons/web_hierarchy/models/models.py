from odoo import api, models
from odoo.fields import Domain


class Base(models.AbstractModel):
    _inherit = 'base'

    def _get_parent_res_id_from_domain(self, domain, parent_field_name):
        """ Return the id of the parent targeted by ``domain``, if any.

        The domain targets a parent when it contains a condition
        ``(parent_field_name, '=', <id>)`` at its first level, i.e. either as
        the whole domain or as a direct operand of its top-level AND. Such a
        condition restricts all the records to the children of that parent.
        Conditions nested under a OR or a NOT, or using another operator, are
        ignored as they do not restrict all the records.

        :param domain: the search domain (list or :class:`Domain`)
        :param str parent_field_name: name of the many2one field to the parent
        :return: the id of the targeted parent, or ``False``
        :rtype: int | bool
        """
        domain = Domain(domain)
        children = domain.children if getattr(domain, 'OPERATOR', None) == '&' else (domain, )
        for child in children:
            if child.is_condition(parent_field_name, '=', int) and child.value:
                return child.value
        return False

    def _hierarchy_read_children(
        self,
        domain,
        specification,
        parent_res_id,
        parent_field_name,
        parent=None,
        offset=0,
        limit=None,
        order=None,
        count_limit=None,
    ):
        """ Read a page of the children of a parent, and the parent itself.

        The children are the records matching ``domain``, which must restrict
        them to the children of ``parent_res_id``. The parent is read
        separately from the children: it is neither part of the page nor
        counted in the length. Both are read with a single ``web_read``.

        When ``parent`` is not given, it is taken from the parent field of the
        first child, which avoids a query; if there is no child on the page,
        it is searched by id. In both cases, a parent the current user cannot
        read is not returned.

        :param domain: domain of the children
        :param dict specification: the ``web_read`` specification
        :param int parent_res_id: id of the parent
        :param str parent_field_name: name of the many2one field to the parent
        :param parent: the parent record, if already known
        :param int offset: number of children to skip
        :param int limit: maximum number of children to return
        :param str order: sort order of the children
        :param int count_limit: maximum number of children to count
        :return: a dict with the keys:
            - ``parent``: the values of the parent, or ``False`` if it is not
            accessible
            - ``records``: the values of the children of the page
            - ``length``: the number of children matching ``domain``
        :rtype: dict
        """
        records = self.search_fetch(domain, list(specification), offset=offset, limit=limit, order=order)
        if parent is None:
            if records:
                parent = records[0][parent_field_name]._filtered_access('read')
            else:
                parent = self.search(Domain('id', '=', parent_res_id))
        values = (parent + records).web_read(specification)
        parent_values, records_values = (values[0], values[1:]) if parent else (False, values)
        return {
            'parent': parent_values,
            **self._format_web_search_read_results(domain, records_values, offset, limit, count_limit),
        }

    @api.model
    def hierarchy_read(
        self,
        domain,
        specification,
        parent_field_name,
        roots_only=False,
        offset=0,
        limit=None,
        order=None,
        count_limit=None,
    ):
        """ Load the data displayed by the hierarchy view.

        Like :meth:`web_search_read`, return a page of records with the total
        length, plus the parent node to display above them. The records depend
        on the following cases, evaluated in that order:

        1. ``domain`` targets a parent (see
        :meth:`_get_parent_res_id_from_domain`): return that parent and a
        page of its children matching ``domain``.
        2. ``roots_only`` is set: only the roots (records without parent)
        matching ``domain`` are considered. If there is a single root, it is
        unfolded: return it as parent with a page of its children. Otherwise,
        return a page of the roots, without parent.
        3. Otherwise: return a page of the records matching ``domain``, without
        parent.

        The page (``offset``, ``limit``, ``order``, ``count_limit``) always
        applies to the returned records, never to the parent. In particular,
        whether there is a single root does not depend on the page.

        :param domain: the search domain
        :param dict specification: the ``web_read`` specification of the
            records and of the parent
        :param str parent_field_name: name of the many2one field to the parent
        :param bool roots_only: whether to restrict the records to the roots,
            typically when the search of the view is the default one
        :param int offset: number of records to skip
        :param int limit: maximum number of records to return
        :param str order: sort order of the records
        :param int count_limit: maximum number of records to count
        :return: a dict with the keys:
            - ``parent``: the values of the parent node, or ``False``
            - ``records``: the values of the records of the page
            - ``length``: the number of records matching the domain
        :rtype: dict
        """
        domain = Domain(domain)
        target_parent_res_id = self._get_parent_res_id_from_domain(domain, parent_field_name)
        read_kwargs = {'offset': offset, 'limit': limit, 'order': order, 'count_limit': count_limit}

        if target_parent_res_id:
            return self._hierarchy_read_children(
                domain, specification, target_parent_res_id, parent_field_name, **read_kwargs,
            )

        if roots_only:
            roots_domain = domain & Domain(parent_field_name, '=', False)
            if not offset and (limit is None or limit > 1):
                roots = self.search_fetch(roots_domain, list(specification), limit=limit, order=order)
                single_root = roots if len(roots) == 1 else None
            else:
                candidates = self.search(roots_domain, limit=2)
                single_root = candidates if len(candidates) == 1 else None
                roots = None

            if single_root:
                return self._hierarchy_read_children(
                    domain & Domain(parent_field_name, '=', single_root.id),
                    specification,
                    single_root.id,
                    parent_field_name,
                    parent=single_root,
                    **read_kwargs,
                )

            if roots is None:
                roots = self.search_fetch(roots_domain, list(specification), offset=offset, limit=limit, order=order)
            return {
                'parent': False,
                **self._format_web_search_read_results(
                    roots_domain, roots.web_read(specification), offset, limit, count_limit,
                ),
            }

        return {'parent': False, **self.web_search_read(domain, specification, **read_kwargs)}
