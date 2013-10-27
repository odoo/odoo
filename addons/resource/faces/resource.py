#@+leo-ver=4
#@+node:@file resource.py
#@@language python
#@<< Copyright >>
#@+node:<< Copyright >>
############################################################################
#   Copyright (C) 2005, 2006, 2007, 2008 by Reithinger GmbH
#   mreithinger@web.de
#
#   This file is part of faces.
#
#   faces is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   faces is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
############################################################################

#@-node:<< Copyright >>
#@nl
#@<< Imports >>
#@+node:<< Imports >>
import pcalendar
import datetime
import utils
import string
import bisect
import plocale
#@-node:<< Imports >>
#@nl

_is_source = True
_to_datetime = pcalendar.to_datetime
_ = plocale.get_gettext()

#@+others
#@+node:_isattrib
#@+doc
#@nonl
# is used to find snapshot attributes
#@-doc
#@@code
def _isattrib(obj, a):
    return a[0] != "_" \
           and not callable(getattr(obj, a)) \
           and not a.endswith("_members") \
           and a not in ("name")
#@-node:_isattrib
#@+node:class ResourceCalendar
class ResourceCalendar(object):
    """
    The resource calendar saves the load time of a resource.
    Is ia sequence of time intervals of loads. An example of
    such a sequence is:
        [ (datetime.min, 0),
          (2006/1/1, 1.0),
          (2006/1/10, 0.5),
          (2006/1/15, 0) ]

    That means the resource:
        is free till january the first 2006
        is fully booked from january the first to january 10th
        is half booked from january 10th to january 15th
        is free since january 15th
    """

    #@	@+others
    #@+node:__init__
    def __init__(self, src=None):
        if src:
            self.bookings = list(src.bookings)
        else:
            self.bookings = [ (datetime.datetime.min, 0) ]
    #@-node:__init__
    #@+node:__str__
    def __str__(self):
        return str(self.bookings)
    #@-node:__str__
    #@+node:__repr__
    def __repr__(self):
        return "<ResourceCalendar %s>" % (str(self))
    #@-node:__repr__
    #@+node:add_load
    def add_load(self, start, end, load):
        start = _to_datetime(start)
        end = _to_datetime(end)

        bookings = self.bookings

        # the load will be converted in an integer to avoid
        # rouning problems
        load = int(load * 10000)

        start_item = (start, 0)
        start_pos = bisect.bisect_left(bookings, start_item)

        left_load = 0
        left_load = bookings[start_pos - 1][1]

        if start_pos < len(bookings) and bookings[start_pos][0] == start:
            prev_load = bookings[start_pos][1]
            if prev_load + load == left_load:
                del bookings[start_pos]
            else:
                bookings[start_pos] = (start, prev_load + load)
                start_pos += 1
        else:
            bookings.insert(start_pos, (start, load + left_load))
            start_pos += 1

        item = (datetime.datetime.min, 0)
        for i in range(start_pos, len(bookings)):
            end_pos = i
            item = bookings[i]
            if item[0] >= end: break
            bookings[i] = (item[0], item[1] + load)
        else:
            end_pos = len(bookings)

        left_load = bookings[end_pos - 1][1]
        if item[0] == end:
            if item[1] == left_load:
                del bookings[end_pos]
        else:
            bookings.insert(end_pos, (end, left_load - load))
    #@-node:add_load
    #@+node:end_of_booking_interval
    def end_of_booking_interval(self, date):
        date = _to_datetime(date)
        bookings = self.bookings
        date_item = (date, 999999)
        date_pos = bisect.bisect_left(bookings, date_item) - 1
        next_date = datetime.datetime.max
        load = 0

        try:
            book_item = bookings[date_pos]
            load = bookings[date_pos][1] / 10000.0
            next_date = bookings[date_pos + 1][0]
        except:
            pass

        return next_date, load
    #@-node:end_of_booking_interval
    #@+node:find_free_time
    def find_free_time(self, start, length, load, max_load):
        bookings = self.bookings

        if isinstance(start, datetime.datetime):
            adjust_date = _to_datetime
        else:
            adjust_date = start.calendar.EndDate

        start = _to_datetime(start)
        load = int(load * 10000)
        max_load = int(max_load * 10000)
        lb = len(bookings)

        def next_possible(index):
            while index < lb:
                sd, lo = bookings[index]
                if lo + load <= max_load:
                    break

                index += 1

            sd = adjust_date(max(start, sd))
            ed = sd + length
            end = _to_datetime(ed)

            index += 1
            while index < lb:
                date, lo = bookings[index]

                if date >= end:
                    #I found a good start date
                    return None, sd

                if lo + load > max_load:
                    return index + 1, None

                index += 1

            return None, sd

        start_item = (start, 1000000)
        i = bisect.bisect_left(bookings, start_item) - 1

        next_start = None
        while not next_start and i < lb:
            i, next_start = next_possible(i)

        assert(next_start is not None)
        return next_start
    #@-node:find_free_time
    #@+node:get_bookings
    def get_bookings(self, start, end):
        start = _to_datetime(start)
        end = _to_datetime(end)
        bookings = self.bookings
        start_item = (start, 0)
        start_pos = bisect.bisect_left(bookings, start_item)
        if start_pos >= len(bookings) or bookings[start_pos][0] > start:
            start_pos -= 1

        end_item = (end, 0)
        end_pos = bisect.bisect_left(bookings, end_item)
        return start_pos, end_pos, bookings
    #@-node:get_bookings
    #@+node:get_load
    def get_load(self, date):
        date = _to_datetime(date)
        bookings = self.bookings
        item = (date, 100000)
        pos = bisect.bisect_left(bookings, item) - 1
        return bookings[pos][1] / 10000.0
    #@-node:get_load
    #@-others
#@-node:class ResourceCalendar
#@+node:class _ResourceBase
class _ResourceBase(object):
    pass

#@-node:class _ResourceBase
#@+node:class _MetaResource
class _MetaResource(type):
    doc_template = """
    A resource class. The resources default attributes can
    be changed when the class ist instanciated, i.e.
    %(name)s(max_load=2.0)

    @var max_load:
    Specify the maximal allowed load sum of all simultaneously
    allocated tasks of a resource. A ME{max_load} of 1.0 (default)
    means the resource may be fully allocated. A ME{max_load} of 1.3
    means the resource may be allocated with 30%% overtime.

    @var title:
    Specifies an alternative more descriptive name for the task.

    @var efficiency:
    The efficiency of a resource can be used for two purposes. First
    you can use it as a crude way to model a team. A team of 5 people
    should have an efficiency of 5.0. Keep in mind that you cannot
    track the member of the team individually if you use this
    feature. The other use is to model performance variations between
    your resources.

    @var vacation:
    Specifies the vacation of the resource. This attribute is
    specified as a list of date literals or date literal intervals.
    Be aware that the end of an interval is excluded, i.e. it is
    the first working date.
    """

    #@	@+others
    #@+node:__init__
    def __init__(self, name, bases, dict_):
        super(_MetaResource, self).__init__(name, bases, dict_)
        self.name = name
        self.title = dict_.get("title", name)
        self._calendar = { None: ResourceCalendar() }
        self._tasks = { }
        self.__set_vacation()
        self.__add_resource(bases[0])
        self.__doc__ = dict_.get("__doc__", self.doc_template) % locals()
    #@-node:__init__
    #@+node:__or__
    def __or__(self, other):
        return self().__or__(other)
    #@-node:__or__
    #@+node:__and__
    def __and__(self, other):
        return self().__and__(other)
    #@-node:__and__
    #@+node:__cmp__
    def __cmp__(self, other):
        return cmp(self.name, getattr(other, "name", None))
    #@-node:__cmp__
    #@+node:__repr__
    def __repr__(self):
        return "<Resource %s>" % self.name
    #@-node:__repr__
    #@+node:__str__
    def __str__(self):
        return repr(self)
    #@-node:__str__
    #@+node:__set_vacation
    def __set_vacation(self):
        vacation = self.vacation

        if isinstance(vacation, (tuple, list)):
            for v in vacation:
                if isinstance(v, (tuple, list)):
                    self.add_vacation(v[0], v[1])
                else:
                    self.add_vacation(v)
        else:
            self.add_vacation(vacation)
    #@-node:__set_vacation
    #@+node:__add_resource
    def __add_resource(self, base):
        if issubclass(base, _ResourceBase):
            members = getattr(base, base.__name__ + "_members", [])
            members.append(self)
            setattr(base, base.__name__ + "_members", members)
    #@-node:__add_resource
    #@+node:get_members
    def get_members(self):
        return getattr(self, self.__name__ + "_members", [])
    #@-node:get_members
    #@+node:add_vacation
    def add_vacation(self, start, end=None):
        start_date = _to_datetime(start)

        if not end:
            end_date = start_date.replace(hour=23, minute=59)
        else:
            end_date = _to_datetime(end)

        for cal in self._calendar.itervalues():
            cal.add_load(start_date, end_date, 1)

        tp = Booking()
        tp.start = start_date
        tp.end = end_date
        tp.book_start = start_date
        tp.book_end = end_date
        tp.work_time = end_date - start_date
        tp.load = 1.0
        tp.name = tp.title = _("(vacation)")
        tp._id = ""
        self._tasks.setdefault("", []).append(tp)
    #@-node:add_vacation
    #@+node:calendar
    def calendar(self, scenario):
        try:
            return self._calendar[scenario]
        except KeyError:
            cal = self._calendar[scenario] = ResourceCalendar(self._calendar[None])
            return cal

    #@-node:calendar
    #@-others
#@-node:class _MetaResource
#@+node:make_team
def make_team(resource):
    members = resource.get_members()
    if not members:
        return resource

    result = make_team(members[0])
    for r in members[1:]:
        result = result & make_team(r)

    return result
#@-node:make_team
#@+node:class Booking
class Booking(object):
    """
    A booking unit for a task.
    """
    #@	<< declarations >>
    #@+node:<< declarations >>
    book_start = datetime.datetime.min
    book_end = datetime.datetime.max
    actual = False
    _id = ""

    #@-node:<< declarations >>
    #@nl
    #@	@+others
    #@+node:__init__
    def __init__(self, task=None):
        self.__task = task
    #@-node:__init__
    #@+node:__cmp__
    def __cmp__(self, other):
        return cmp(self._id, other._id)
    #@-node:__cmp__
    #@+node:path
    def path(self):
        first_dot = self._id.find(".")
        return "root" + self._id[first_dot:]

    path = property(path)
    #@nonl
    #@-node:path
    #@+node:_idendity_
    def _idendity_(self):
        return self._id
    #@-node:_idendity_
    #@+node:__getattr__
    def __getattr__(self, name):
        if self.__task:
            return getattr(self.__task, name)

        raise AttributeError("'%s' is not a valid attribute" % (name))
    #@-node:__getattr__
    #@-others
#@-node:class Booking
#@+node:class ResourceList
class ResourceList(list):
    #@	@+others
    #@+node:__init__
    def __init__(self, *args):
        if args: self.extend(args)
    #@-node:__init__
    #@-others
#@-node:class ResourceList
#@+node:class Resource
class Resource(_ResourceBase):
    #@	<< declarations >>
    #@+node:<< declarations >>
    __metaclass__ = _MetaResource
    __attrib_completions__ = {\
        "max_load": 'max_load = ',
        "title":  'title = "|"',
        "efficiency": 'efficiency = ',
        "vacation": 'vacation = [("|2002-02-01", "2002-02-05")]' }

    __type_image__ = "resource16"

    max_load = None # the maximum sum load for all task
    vacation = ()
    efficiency = 1.0


    #@-node:<< declarations >>
    #@nl
    #@	@+others
    #@+node:__init__
    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
    #@-node:__init__
    #@+node:_idendity_
    def _idendity_(cls):
        return "resource:" + cls.__name__

    _idendity_ = classmethod(_idendity_)
    #@-node:_idendity_
    #@+node:__repr__
    def __repr__(self):
        return "<Resource %s>" % self.__class__.__name__
    #@-node:__repr__
    #@+node:__str__
    def __str__(self):
        return repr(self)
    #@-node:__str__
    #@+node:__call__
    def __call__(self):
        return self
    #@-node:__call__
    #@+node:__hash__
    def __hash__(self):
        return hash(self.__class__)
    #@-node:__hash__
    #@+node:__cmp__
    def __cmp__(self, other):
        return cmp(self.name, other.name)
    #@-node:__cmp__
    #@+node:__or__
    def __or__(self, other):
        if type(other) is _MetaResource:
            other = other()

        result = Resource()
        result._subresource = _OrResourceGroup(self, other)
        return result
    #@-node:__or__
    #@+node:__and__
    def __and__(self, other):
        if type(other) is _MetaResource:
            other = other()

        result = Resource()
        result._subresource = _AndResourceGroup(self, other)
        return result
    #@-node:__and__
    #@+node:_permutation_count
    def _permutation_count(self):
        if hasattr(self, "_subresource"):
            return self._subresource._permutation_count()

        return 1
    #@-node:_permutation_count
    #@+node:_get_resources
    def _get_resources(self, state):
        if hasattr(self, "_subresource"):
            result = self._subresource._get_resources(state)

            if self.name != "Resource":
                result.name = self.name

            if self.title != "Resource":
                result.title = self.title

            return result

        result = ResourceList(self)
        return result
    #@-node:_get_resources
    #@+node:all_members
    def all_members(self):
        if hasattr(self, "_subresource"):
            return self._subresource.all_members()

        return [ self.__class__ ]
    #@-node:all_members
    #@+node:unbook_tasks_of_project
    def unbook_tasks_of_project(cls, project_id, scenario):
        try:
            task_list = cls._tasks[scenario]
        except KeyError:
            return

        add_load = cls.calendar(scenario).add_load
        for task_id, bookings in task_list.items():
            if task_id.startswith(project_id):
                for item in bookings:
                    add_load(item.book_start, item.book_end, -item.load)

                del task_list[task_id]

        if not task_list:
            del cls._tasks[scenario]

    unbook_tasks_of_project = classmethod(unbook_tasks_of_project)
    #@-node:unbook_tasks_of_project
    #@+node:unbook_task
    def unbook_task(cls, task):
        identdity = task._idendity_()
        scenario = task.scenario

        try:
            task_list = cls._tasks[scenario]
            bookings = task_list[identdity]
        except KeyError:
            return

        add_load = cls.calendar(scenario).add_load
        for b in bookings:
            add_load(b.book_start, b.book_end, -b.load)

        del task_list[identdity]
        if not task_list:
            del cls._tasks[scenario]

    unbook_task = classmethod(unbook_task)
    #@-node:unbook_task
    #@+node:correct_bookings
    def correct_bookings(cls, task):
        #correct the booking data with the actual task data
        try:
            tasks = cls._tasks[task.scenario][task._idendity_()]
        except KeyError:
            return

        for t in tasks:
            t.start = task.start.to_datetime()
            t.end = task.end.to_datetime()

    correct_bookings = classmethod(correct_bookings)
    #@-node:correct_bookings
    #@+node:book_task
    def book_task(cls, task, start, end, load, work_time, actual):
        if not work_time: return

        start = _to_datetime(start)
        end = _to_datetime(end)

        identdity = task._idendity_()
        task_list = cls._tasks.setdefault(task.scenario, {})
        bookings = task_list.setdefault(identdity, [])
        add_load = cls.calendar(task.scenario).add_load

        tb = Booking(task)
        tb.book_start = start
        tb.book_end = end
        tb._id = identdity
        tb.load = load
        tb.start = _to_datetime(task.start)
        tb.end = _to_datetime(task.end)
        tb.title = task.title
        tb.name = task.name
        tb.work_time = int(work_time)
        tb.actual = actual
        bookings.append(tb)
        result = add_load(start, end, load)
        return result

    book_task = classmethod(book_task)
    #@-node:book_task
    #@+node:length_of
    def length_of(cls, task):
        cal = task.root.calendar
        bookings = cls.get_bookings(task)
        return sum(map(lambda b: task._to_delta(b.work_time).round(), bookings))

    length_of = classmethod(length_of)
    #@-node:length_of
    #@+node:done_of
    def done_of(self, task):
        cal = task.root.calendar
        now = cal.now
        bookings = self.get_bookings(task)

        if task.__dict__.has_key("effort"):
            efficiency = self.efficiency * task.efficiency
        else:
            efficiency = 1

        def book_done(booking):
            if booking.book_start >= now:
                return 0

            factor = 1
            if booking.book_end > now:
                start = task._to_start(booking.book_start)
                end = task._to_end(booking.book_end)
                cnow = task._to_start(now)
                factor = float(cnow - start) / ((end - start) or 1)

            return factor * booking.work_time * efficiency

        return task._to_delta(sum(map(book_done, bookings)))
    #@-node:done_of
    #@+node:todo_of
    def todo_of(self, task):
        cal = task.root.calendar
        now = cal.now

        bookings = self.get_bookings(task)
        if task.__dict__.has_key("effort"):
            efficiency = self.efficiency * task.efficiency
        else:
            efficiency = 1

        def book_todo(booking):
            if booking.book_end <= now:
                return 0

            factor = 1
            if booking.book_start < now:
                start = task._to_start(booking.book_start)
                end = task._to_end(booking.book_end)
                cnow = task._to_start(now)
                factor = float(end - cnow) / ((end - start) or 1)

            return factor * booking.work_time * efficiency

        return task._to_delta(sum(map(book_todo, bookings)))
    #@-node:todo_of
    #@+node:get_bookings
    def get_bookings(cls, task):
        return cls._tasks.get(task.scenario, {}).get(task._idendity_(), ())

    get_bookings = classmethod(get_bookings)
    #@-node:get_bookings
    #@+node:get_bookings_at
    def get_bookings_at(cls, start, end, scenario):
        result = []

        try:
            items = cls._tasks[scenario].iteritems()
        except KeyError:
            return ()

        for task_id, bookings in items:
            result += [ booking for booking in bookings
                        if booking.book_start < end
                        and booking.book_end > start ]

        vacations = cls._tasks.get("", ())
        result += [ booking for booking in vacations
                    if booking.book_start < end
                    and booking.book_end > start ]

        return result

    get_bookings_at = classmethod(get_bookings_at)
    #@-node:get_bookings_at
    #@+node:find_free_time
    def find_free_time(cls, start, length, load, max_load, scenario):
        return cls.calendar(scenario).find_free_time(start, length, load, max_load)

    find_free_time = classmethod(find_free_time)
    #@-node:find_free_time
    #@+node:get_load
    def get_load(cls, date, scenario):
        return cls.calendar(scenario).get_load(date)

    get_load = classmethod(get_load)
    #@-node:get_load
    #@+node:end_of_booking_interval
    def end_of_booking_interval(cls, date, task):
        return cls.calendar(task.scenario).end_of_booking_interval(date)

    end_of_booking_interval = classmethod(end_of_booking_interval)
    #@-node:end_of_booking_interval
    #@+node:snapshot
    def snapshot(self):
        from task import _as_string
        def isattrib(a):
            if a == "max_load" and self.max_load is None: return False
            if a in ("name", "title", "vacation"): return False
            return _isattrib(self, a)

        attribs = filter(isattrib, dir(self))
        attribs = map(lambda a: "%s=%s" % (a, _as_string(getattr(self, a))),
                      attribs)

        return self.name + "(%s)" % ", ".join(attribs)
    #@-node:snapshot
    #@-others
#@-node:class Resource
#@+node:class _ResourceGroup


class _ResourceGroup(object):
    #@	@+others
    #@+node:__init__
    def __init__(self, *args):
        self.resources = []
        for a in args:
            self.__append(a)
    #@-node:__init__
    #@+node:all_members
    def all_members(self):
        group = reduce(lambda a, b: a + b.all_members(),
                       self.resources, [])
        group = map(lambda r: (r, True), group)
        group = dict(group)
        group = group.keys()
        return group
    #@-node:all_members
    #@+node:_permutation_count
    def _permutation_count(self):
        abstract
    #@-node:_permutation_count
    #@+node:_refactor
    def _refactor(self, arg):
        pass
    #@-node:_refactor
    #@+node:__append
    def __append(self, arg):
        if isinstance(arg, self.__class__):
            self.resources += arg.resources
            for r in arg.resources:
                self._refactor(r)
            return
        elif isinstance(arg, Resource):
            subresources = getattr(arg, "_subresource", None)
            if subresources:
                self.__append(subresources)
                return
            else:
                self.resources.append(arg)
        else:
            assert(isinstance(arg, _ResourceGroup))
            self.resources.append(arg)

        self._refactor(arg)
    #@-node:__append
    #@+node:__str__
    def __str__(self):
        op = lower(self.__class__.__name__[0:-13])
        return "(" + \
               string.join([str(r) for r in self.resources],
                           " " + op + " ") + \
               ")"
    #@-node:__str__
    #@-others
#@-node:class _ResourceGroup
#@+node:class _OrResourceGroup


class _OrResourceGroup(_ResourceGroup):
    #@	@+others
    #@+node:_get_resources
    def _get_resources(self, state):
        for r in self.resources:
            c = r._permutation_count()
            if c <= state:
                state -= c
            else:
                return r._get_resources(state)

        assert(0)
    #@-node:_get_resources
    #@+node:_permutation_count
    def _permutation_count(self):
        return sum([ r._permutation_count() for r in self.resources])
    #@-node:_permutation_count
    #@-others
#@-node:class _OrResourceGroup
#@+node:class _AndResourceGroup


class _AndResourceGroup(_ResourceGroup):
    #@	@+others
    #@+node:__init__
    def __init__(self, *args):
        self.factors = [ 1 ]
        _ResourceGroup.__init__(self, *args)
    #@-node:__init__
    #@+node:_refactor
    def _refactor(self, arg):
        count = arg._permutation_count()
        self.factors = [ count * f for f in self.factors ]
        self.factors.append(1)
    #@-node:_refactor
    #@+node:_permutation_count
        #print "AndResourceGroup", count, arg, self.factors


    def _permutation_count(self):
        return self.factors[0]
    #@-node:_permutation_count
    #@+node:_get_resources
    def _get_resources(self, state):
        """delivers None when there are duplicate resources"""
        result = []
        for i in range(1, len(self.factors)):
            f = self.factors[i]
            substate = state / f
            state %= f
            result.append(self.resources[i - 1]._get_resources(substate))

        result = ResourceList(*list(utils.flatten(result)))
        dupl_test = { }
        for r in result:
            if dupl_test.has_key(r):
                return None
            else:
                dupl_test[r] = 1

        return result
    #@-node:_get_resources
    #@+node:_has_duplicates
    def _has_duplicates(self, state):
        resources = self._get_resources(state)
        tmp = { }
        for r in resources:
            if tmp.has_key(r):
                return True

            tmp[r] = 1

        return False
    #@-node:_has_duplicates
    #@-others
#@-node:class _AndResourceGroup
#@-others
#@-node:@file resource.py
#@-leo

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
