# -*- coding: utf-8 -*-

from odoo import models, fields, api

class test(models.Model):
    _name = 'test'

    name = fields.Char()
    line_ids = fields.One2many('test.line', 'test_id')

    int1 = fields.Integer('User', default=lambda x: 1)
    intx2 = fields.Integer('User', compute="_line_x2", store=True)

    line_sum = fields.Integer('Sum Currency', compute='_line_sum', store=True)

    @api.depends('line_ids.intx2')
    def _line_sum(self):
        for record in self:
            total = 0
            for line in record.line_ids:
                total += line.intx2
            record.line_sum = total

    @api.depends('source')
    def _get_intx2(self):
        for record in self:
            record.intx2 = int1 * 2

    def testme(self):
        main_id = self.create({
            'name': 'bla',
            'line_ids': [
                (0,0, {'name': 'abc'}),
                (0,0, {'name': 'def'}),
            ]
        })
        main_id.int1 = 5
        self.env['test.line'].create(
            {'name': 'ghi', 'test_id': main_id.id}
        )
        self.env['test.line'].search([('intx2', '=', 3)])
        return True


class test_line(models.Model):
    _name = 'test.line'

    name = fields.Char()
    test_id = fields.Many2one('test')
    intx2   = fields.Integer(compute='_get_intx2', store=True)

    @api.depends('test_id.intx2')
    def _get_intx2(self):
        for record in self:
            record.intx2 = record.test_id.intx2

# ------------------------------------------ Status ----------------------------------------

when self.testme()
- master:              32 SQL
- master-nochange-fp:  15 SQL
- future:               8 SQL


for partner in self.env['res.partner'].search([]):
    partner.country_id.name

# -------------------------------- Simplified Execution Trace --------------------------------

- ecriture    -> modified -> todo
- compute     -> lecture / search / commit() / read_group (or is it search?)
- consistency -> create() / new()
- compute ->
    1/ compute don't return
    2/ don't overwrite what you receive
- browse() should use _read() instead of read()
- _prefetch() -> autrement
- recursive   -> ???
- protected   -> ???
- in_draft    -> not record.id
- modified    -> read inverse field
- towrite     -> journal  --> optimization --> _read(), search()
- mettre à jour la cache aux écritures
- cache       -> sudo() / Exception()

# -------------------------------- Simplified Execution Trace --------------------------------

main = test.create({...})
    test._create()                                                                              # stored fields only (not one2many, ...)
        cr.execute("INSERT INTO test (name, int1)")
    self.env.cache.set(self, test_int1, 5)                                                      # put in cache created values
    self.env.cache.set(self, test_name, 'bla')
    self.env.cache.set(self, test_line_ids, [])                                                 # empty one2many, many2many
    env.all.todo.add(['intx2', 'line_sum'])                                                     # we could todo.add all non provided computed fields, if we want default methods to become computed fields
    field_line_ids.create()                                                                     # can we remove the create method on fields? the behavior of write/create is the same, no?
        field_line_ids._write()
            test_line.create({'test_id': 1, 'name': 'abc'}, {'test_id': 1, 'name': 'def'})
                test_line._create()
                    cr.execute("INSERT INTO test.line (name, test_id) values ('abc', 1)")
                    cr.execute("INSERT INTO test.line (name, test_id) values ('def', 1)")
                self.cache[(line_name, 1)] = 'abc'
                self.cache[(line_test_id, 1)] = 1
                self.cache[(line_name, 2)] = 'def'
                self.cache[(line_test_id, 2)] = 1
                ??? add_to_inverse (order not set)                                              # -- SOIT tant pis (spec change), SOIT SQL à la main
                self.modified(['name', 'test_id'])
                    env.all.todo.add((field_intx2, test_lines))
                    self.modified(field_intx2)
                        for test in self.mapped('test_id'):                                     # inverse field of line_sum's line_ids = test_id --> no select as already in cache
                            env.all.todo.add((field_line_sum, test))
    test.modified(['name', 'int1'])                                                             # all stored - one2many are not considered mdified (as no many2one points to them yet)
        env.all.todo.add((field_intx2, test))
        test.modified(['intx2'])                                                                # modified is recursive, until all impacted records are in todo (we loose the advantage of do not write if same value)
            pass                                                                                # no record impacted as triggers just read inverse fields and line_ids=[]

main.int1 = 5
    field_int1.__set__()
        env.all.todo.remove((self, record))
        if not self.cache.contains((int1, 1)) or self.cache[(int1, 1)] != 5                     # if value did not changed in cache
            self.cache[(int1, 1)] = 5
            env.towrite.append(int1, 1, 5)                                                      # journal of stuff to write: should be an ordered dict
            self.modified(['int1'])
                env.all.todo.add((field_intx2, test))
                self.modified(field_intx2)
                    for line in self.mapped('line_ids'):                                        # inverse field of line_intx2's line_ids = test_id
                        if env.all.todo.add.contains((field_intx2, test_lines)):                # modified are recursive...
                            pass                                                                # and stops if field is already marked as todo
        env.all.todo.remove((self, record))                                                     # this replace the protected

line.create({...})
    line._create()
        cr.execute("INSERT INTO test.line (name, test_id) values ('ghi', 1)")
    self.cache[(line_name, 3)] = 'ghi'
    self.cache[(line_test_id, 3)] = 1
    ??? add to inverse                                                                          # as we wrote a value on test_id, we should update line_ids
    test_line.modified(['name', 'test_id'])
        env.all.todo.add((field_intx2, test_line))
        for test in self.mapped('test_id'):                                                     # inverse field of line_sum's line_ids = test_id
            env.all.todo.add((field_line_sum, test))

line.search([('intx2', '=', 3)])
    for field in dom_args if field in env.all.todo: field.check_todo()
        recs = self.env.field_todo(field)                                                       # return all 3 lines
        field.compute_value(recs)
            fields = records._field_computed(self)                                              # all fields that are computed together
            env.all.todo.remove(fields, records)                                                # the todo should be removed here, not at the __set__ as a compute might not return a value
            line._get_intx2()
                record.intx2 = record.test_id.intx2
                    test_id.intx2.__get__()
                        if self.env.check_todo():                                               # test.intx2 must be computed
                            recs = self.env.field_todo(field_intx2)
                            field_intx2.compute_value(recs)
                                fields = records._field_computed(self)
                                env.all.todo.remove(fields, records)
                                test._get_intx2()
                                    record.intx2 = int1 * 2
                                        intx2.__set__()
                                            self.cache[(int1, 1)] = 10
                                            env.towrite.append((intx2, 1), 10)                  # or we use the cache for towrite?
                                            self.modified(['intx2'])                            # that is a waste of time, if we already modified recursively
                    intx2.__set__()                                                             # write intx2 on lines
                        self.cache[(int1, 1)] = 10
                        env.towrite.append((intx2, 1), 10)                                      # or we use the cache for towrite?
                        # self.modified(['intx2'])                                              # that is a waste of time, if we already modified recursively, unless it's 
    self.flush_write()
        while env.towrite():
            # optimize to work in batches
            self._write()
                cr.execute("UPDATE test.test SET intx2=10, int1=5 WHERE id=1")
            self._write()
                cr.execute("UPDATE test.line SET intx2=10 where id in (...)")

    cr.execute('SELECT ...')


recompute()                                                                                     # in api.py
    while env.has_todo():
        field_line_sum.compute_value(recs)                                                      # only line_sum should remain
            fields = records._field_computed(self)                                              # all fields that are computed together
            env.all.todo.remove(fields, records)                                                # the todo should be removed here, not at the __set__ as a compute might not return a value
            records._line_sum()
                record.line_sum = total
                    line_sum.__set__()
                        self.cache[(int1, 1)] = 20
                        env.towrite.append((intx2, 1), 20)
                        # self.modified(['intx2'])                                              # that is a waste of time, if we already modified recursively
    self.flush_write()
        while env.towrite():
            # optimize to work in batches
            self._write()
                cr.execute("UPDATE test.test SET line_sum=10 WHERE id=1")


def __get__()
    if todo:
        compute()
    if cache
        return cache.get()
    else:
        _read()



# --------------------------------------- To discuss with RCOs ------------------------------------

# Questions

- What is a SpecialValue in cache? (update inverse lazy)
    AccessRights
    MissingRecords
    Exception in a compute


# Reading optimization

- browse should call _read, not read()
    -> check help in ir.actions (overwrite of read())
- replace prefetch by larger recordset with self._id: records.country_ids returns a recordset with all countries; id is just a position on this recordset ([0] and next() returns the same recordset with a different id)
- access rights --> check once at exposed method level? still not sure

# Writing optimization

- onchange use new(), and new() use default()  (new() and create() should be compatible) --> RCO's branch
    - consistent
- remove the prefetch concept: records.country_id should return a RecordSet with all countries of records (id is a cursor on the actual record) --> RCO's branch
- in draft is not required anymore? (if not record.id: don't add value in towrite)
- why do we need protected? to evaluate
- why is sequence of fields used? looks like we can remove that concept (min())
- recursive modified: extra cost, that will limit the impact of "do not update if value did not changed"
- behavior change: compute might not return a value (necessary for onchange)
- if I am not wrong, recursive should not require a specific mechanism with this approach
- what do we do when we have no inverse field? (fault back to SQL triggers, or create an implicit one just for the cache)
    - faultback
- towrite should be processed before an unlink or a select
- related = computed fields
- Cache by environments or not, or partial (improve context_dependent?)
    - should compute, non stored fields, be in the cache? (as their computation already rely on other's fields cache) --> slower, but remove context_dependant issues
    - one2many / many2many should not be context_dependent, but many2many yes
- rename todo into torecompute
- do we really need SpecialValue in cache? yes
- dirty: to remove


# --------------------------------- DECIDE LATER ----------------------------

- sudo() should not change the uid (but keep applying ir.rule or not, à tester)
    - sudo(user=admin)
- default methods can be just a compute method without @depends(), to simplify the framework and consistency
- Syntax of new compute fields: 3 option
    1/ related_onchange="partner_id.fp_id"
    2/ explicit compute="" with method and @depends
    3/ readonly=False, depends=['partner_id'], related="partner_id.fp_id"


# -------------------------------- WRITE -------------------------------------

Master
    def write():
        inverse_fields.clear_cache()
        self.cache_set()
        self._write()
        inverse_fields.update()
        self.modified(vals)
        inherits.write(...)                          # not in __set__ -> via inverse fields
        inverse_fields.inverse()                     # not in __set__

    def _write():
        self.check_access_rights()
        cr.execute(...)
        translation_update
        self.validate()
        self.parent_store()

    def __set__():
        if old_value == new_value: continue
        inverse_fields.clear_cache()
        self.cache_set()
        inverse_fields.update()
        self.modified(vals)

# Goal: replace self.write() by:

def write(self, values):
    for key, val in values:
        self[key] = val


-> perform inverse in __set__
-> inherits through inverse methods















