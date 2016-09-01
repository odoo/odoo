# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of connector, an Odoo module.
#
#     Author: Stéphane Bidoul <stephane.bidoul@acsone.eu>
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     connector is free software: you can redistribute it and/or
#     modify it under the terms of the GNU Affero General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     connector is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the
#     GNU Affero General Public License
#     along with connector.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from heapq import heappush, heappop
import logging
from weakref import WeakValueDictionary

from ..exception import ChannelNotFound
from ..queue.job import PENDING, ENQUEUED, STARTED, FAILED, DONE
NOT_DONE = (PENDING, ENQUEUED, STARTED, FAILED)

_logger = logging.getLogger(__name__)


class PriorityQueue(object):
    """A priority queue that supports removing arbitrary objects.

    Adding an object already in the queue is a no op.
    Popping an empty queue returns None.

    >>> q = PriorityQueue()
    >>> q.add(2)
    >>> q.add(3)
    >>> q.add(3)
    >>> q.add(1)
    >>> q[0]
    1
    >>> len(q)
    3
    >>> q.pop()
    1
    >>> q.remove(2)
    >>> len(q)
    1
    >>> q[0]
    3
    >>> q.pop()
    3
    >>> q.pop()
    >>> q.add(2)
    >>> q.remove(2)
    >>> q.add(2)
    >>> q.pop()
    2
    """

    def __init__(self):
        self._heap = []
        self._known = set()    # all objects in the heap (including removed)
        self._removed = set()  # all objects that have been removed

    def __len__(self):
        return len(self._known) - len(self._removed)

    def __getitem__(self, i):
        if i != 0:
            raise IndexError()
        while True:
            if not self._heap:
                raise IndexError()
            o = self._heap[0]
            if o in self._removed:
                o2 = heappop(self._heap)
                assert o2 == o
                self._removed.remove(o)
                self._known.remove(o)
            else:
                return o

    def __contains__(self, o):
        return o in self._known and o not in self._removed

    def add(self, o):
        if o is None:
            raise ValueError()
        if o in self._removed:
            self._removed.remove(o)
        if o in self._known:
            return
        self._known.add(o)
        heappush(self._heap, o)

    def remove(self, o):
        if o is None:
            raise ValueError()
        if o not in self._known:
            return
        if o not in self._removed:
            self._removed.add(o)

    def pop(self):
        while True:
            try:
                o = heappop(self._heap)
            except IndexError:
                # queue is empty
                return None
            self._known.remove(o)
            if o in self._removed:
                self._removed.remove(o)
            else:
                return o


class SafeSet(set):
    """A set that does not raise KeyError when removing non-existent items.

    >>> s = SafeSet()
    >>> s.remove(1)
    >>> len(s)
    0
    >>> s.remove(1)
    """
    def remove(self, o):
        try:
            super(SafeSet, self).remove(o)
        except KeyError:
            pass


class ChannelJob(object):
    """A channel job is attached to a channel and holds the properties of a
    job that are necessary to prioritise them.

    Channel jobs are comparable according to the following rules:
        * jobs with an eta come before all other jobs
        * then jobs with a smaller eta come first
        * then jobs with smaller priority come first
        * then jobs with a smaller creation time come first
        * then jobs with a smaller sequence come first

    Here are some examples.

    j1 comes before j2 before it has a smaller date_created

    >>> j1 = ChannelJob(None, None, 1,
    ...                 seq=0, date_created=1, priority=9, eta=None)
    >>> j1
    <ChannelJob 1>
    >>> j2 = ChannelJob(None, None, 2,
    ...                 seq=0, date_created=2, priority=9, eta=None)
    >>> j1 < j2
    True

    j3 comes first because it has lower priority,
    despite having a creation date after j1 and j2

    >>> j3 = ChannelJob(None, None, 3,
    ...                 seq=0, date_created=3, priority=2, eta=None)
    >>> j3 < j1
    True

    j4 and j5 comes even before j3, because they have an eta

    >>> j4 = ChannelJob(None, None, 4,
    ...                 seq=0, date_created=4, priority=9, eta=9)
    >>> j5 = ChannelJob(None, None, 5,
    ...                 seq=0, date_created=5, priority=9, eta=9)
    >>> j4 < j5 < j3
    True

    j6 has same date_created and priority as j5 but a smaller eta

    >>> j6 = ChannelJob(None, None, 6,
    ...                 seq=0, date_created=5, priority=9, eta=2)
    >>> j6 < j4 < j5
    True

    Here is the complete suite:

    >>> j6 < j4 < j5 < j3 < j1 < j2
    True

    j0 has the same properties as j1 but they are not considered
    equal as they are different instances

    >>> j0 = ChannelJob(None, None, 1,
    ...                 seq=0, date_created=1, priority=9, eta=None)
    >>> j0 == j1
    False
    >>> j0 == j0
    True
    """

    def __init__(self, db_name, channel, uuid,
                 seq, date_created, priority, eta):
        self.db_name = db_name
        self.channel = channel
        self.uuid = uuid
        self.seq = seq
        self.date_created = date_created
        self.priority = priority
        self.eta = eta

    def __repr__(self):
        return "<ChannelJob %s>" % self.uuid

    def __eq__(self, other):
        return id(self) == id(other)

    def __hash__(self):
        return id(self)

    def __cmp__(self, other):
        if self.eta and not other.eta:
            return -1
        elif not self.eta and other.eta:
            return 1
        else:
            return (cmp(self.eta, other.eta) or
                    cmp(self.priority, other.priority) or
                    cmp(self.date_created, other.date_created) or
                    cmp(self.seq, other.seq))


class ChannelQueue(object):
    """A channel queue is a priority queue for jobs that returns
    jobs with a past ETA first.

    >>> q = ChannelQueue()
    >>> j1 = ChannelJob(None, None, 1,
    ...                 seq=0, date_created=1, priority=1, eta=10)
    >>> j2 = ChannelJob(None, None, 2,
    ...                 seq=0, date_created=2, priority=1, eta=None)
    >>> j3 = ChannelJob(None, None, 3,
    ...                 seq=0, date_created=3, priority=1, eta=None)
    >>> q.add(j1)
    >>> q.add(j2)
    >>> q.add(j3)

    Wakeup time is the eta of job 1.

    >>> q.get_wakeup_time()
    10

    We have not reached the eta of job 1, so we get job 2.

    >>> q.pop(now=1)
    <ChannelJob 2>

    Wakeup time is still the eta of job 1, and we get job 1 when we are past
    it's eta.

    >>> q.get_wakeup_time()
    10
    >>> q.pop(now=11)
    <ChannelJob 1>

    Now there is no wakeup time anymore, because no job have an eta.

    >>> q.get_wakeup_time()
    0
    >>> q.pop(now=12)
    <ChannelJob 3>
    >>> q.get_wakeup_time()
    0
    >>> q.pop(now=13)
    """

    def __init__(self):
        self._queue = PriorityQueue()
        self._eta_queue = PriorityQueue()

    def __len__(self):
        return len(self._eta_queue) + len(self._queue)

    def __contains__(self, o):
        return o in self._eta_queue or o in self._queue

    def add(self, job):
        if job.eta:
            self._eta_queue.add(job)
        else:
            self._queue.add(job)

    def remove(self, job):
        self._eta_queue.remove(job)
        self._queue.remove(job)

    def pop(self, now):
        if len(self._eta_queue) and self._eta_queue[0].eta <= now:
            return self._eta_queue.pop()
        else:
            return self._queue.pop()

    def get_wakeup_time(self, wakeup_time=0):
        if len(self._eta_queue):
            if not wakeup_time:
                wakeup_time = self._eta_queue[0].eta
            else:
                wakeup_time = min(wakeup_time, self._eta_queue[0].eta)
        return wakeup_time


class Channel(object):
    """A channel for jobs, with a maximum capacity.

    When jobs are created by connector modules, they may be associated
    to a job channel. Jobs with no channel are inserted into the root channel.

    Job channels are joined in a hierarchy down to the root channel.
    When a job channel has available capacity, jobs are dequeued, marked
    as running in the channel and are inserted into the queue of the
    parent channel where they wait for available capacity and so on.

    Job channels can be visualized as water channels with a given flow
    limit (= capacity). Channels are joined together in a downstream channel
    and the flow limit of the downstream channel limits upstream channels.::

        ---------------------+
                             |
                             |
         Ch. A C:4,Q:12,R:4  +-----------------------

        ---------------------+  Ch. root C:5,Q:0,R:4
                             |
        ---------------------+
         Ch. B C:1,Q:0,R:0
        ---------------------+-----------------------

    The above diagram illustrates two channels joining in the root channel.
    The root channel has a capacity of 5, and 4 running jobs coming from
    Channel A. Channel A has a capacity of 4, all in use (passed down to the
    root channel), and 12 jobs enqueued. Channel B has a capacity of 1,
    none in use. This means that whenever a new job comes in channel B,
    there will be available room for it to run in the root channel.

    Note that from the point of view of a channel, 'running' means enqueued
    in the downstream channel. Only jobs marked running in the root channel
    are actually sent to Odoo for execution.

    Should a downstream channel have less capacity than its upstream channels,
    jobs going downstream will be enqueued in the downstream channel,
    and compete normally according to their properties (priority, etc).

    Using this technique, it is possible to enforce sequence in a channel
    with a capacity of 1. It is also possible to dedicate a channel with a
    limited capacity for application-autocreated subchannels
    without risking to overflow the system.
    """

    def __init__(self, name, parent, capacity=None, sequential=False,
                 throttle=0):
        self.name = name
        self.parent = parent
        if self.parent:
            self.parent.children[name] = self
        self.children = {}
        self.capacity = capacity
        self.sequential = sequential
        self.throttle = throttle  # seconds
        self._queue = ChannelQueue()
        self._running = SafeSet()
        self._failed = SafeSet()
        self._pause_until = 0  # utc seconds since the epoch

    def configure(self, config):
        """ Configure a channel from a dictionary.

        Supported keys are:

        * capacity
        * sequential
        """
        assert self.fullname.endswith(config['name'])
        self.capacity = config.get('capacity', None)
        self.sequential = bool(config.get('sequential', False))
        self.throttle = int(config.get('throttle', 0))
        if self.sequential and self.capacity != 1:
            raise ValueError("A sequential channel must have a capacity of 1")

    @property
    def fullname(self):
        """ The full name of the channel, in dot separated notation. """
        if self.parent:
            return self.parent.fullname + '.' + self.name
        else:
            return self.name

    def get_subchannel_by_name(self, subchannel_name):
        return self.children.get(subchannel_name)

    def __str__(self):
        capacity = u'∞' if self.capacity is None else str(self.capacity)
        return "%s(C:%s,Q:%d,R:%d,F:%d)" % (self.fullname,
                                            capacity,
                                            len(self._queue),
                                            len(self._running),
                                            len(self._failed))

    def remove(self, job):
        """ Remove a job from the channel. """
        self._queue.remove(job)
        self._running.remove(job)
        self._failed.remove(job)
        if self.parent:
            self.parent.remove(job)

    def set_done(self, job):
        """ Mark a job as done.

        This removes it from the channel queue.
        """
        self.remove(job)
        _logger.debug("job %s marked done in channel %s",
                      job.uuid, self)

    def set_pending(self, job):
        """ Mark a job as pending.

        This puts the job in the channel queue and remove it
        from parent channels queues.
        """
        if job not in self._queue:
            self._queue.add(job)
            self._running.remove(job)
            self._failed.remove(job)
            if self.parent:
                self.parent.remove(job)
            _logger.debug("job %s marked pending in channel %s",
                          job.uuid, self)

    def set_running(self, job):
        """ Mark a job as running.

        This also marks the job as running in parent channels.
        """
        if job not in self._running:
            self._queue.remove(job)
            self._running.add(job)
            self._failed.remove(job)
            if self.parent:
                self.parent.set_running(job)
            _logger.debug("job %s marked running in channel %s",
                          job.uuid, self)

    def set_failed(self, job):
        """ Mark the job as failed. """
        if job not in self._failed:
            self._queue.remove(job)
            self._running.remove(job)
            self._failed.add(job)
            if self.parent:
                self.parent.remove(job)
            _logger.debug("job %s marked failed in channel %s",
                          job.uuid, self)

    def get_jobs_to_run(self, now):
        """ Get jobs that are ready to run in channel.

        This works by enqueuing jobs that are ready to run in children
        channels, then yielding jobs from the channel queue until
        ``capacity`` jobs are marked running in the channel.

        If the ``throttle`` option is set on the channel, then it yields
        no job until at least throttle seconds have elapsed since the previous
        yield.

        :param now: the current datetime in seconds

        :return: iterator of :py:class:`connector.jobrunner.ChannelJob`
        """
        # enqueue jobs of children channels
        for child in self.children.values():
            for job in child.get_jobs_to_run(now):
                self._queue.add(job)
        # is this channel paused?
        if self.throttle:
            if now < self._pause_until:
                if not self.capacity or len(self._running) < self.capacity:
                    _logger.debug("channel %s paused because of throttle "
                                  "delay between jobs", self)
                return
            else:
                # unpause, this is important to avoid perpetual wakeup
                # while the channel is at full capacity
                self._pause_until = 0
        # sequential channels block when there are failed jobs
        # TODO: this is probably not sufficient to ensure
        #       sequentiality because of the behaviour in presence
        #       of jobs with eta; plus: check if there are no
        #       race conditions.
        if self.sequential and len(self._failed):
            return
        # yield jobs that are ready to run, while we have capacity
        while not self.capacity or len(self._running) < self.capacity:
            job = self._queue.pop(now)
            if not job:
                return
            self._running.add(job)
            _logger.debug("job %s marked running in channel %s",
                          job.uuid, self)
            yield job
            if self.throttle:
                self._pause_until = now + self.throttle
                return

    def get_wakeup_time(self, wakeup_time=0):
        if self.capacity and len(self._running) >= self.capacity:
            # this channel is full, do not request timed wakeup, as
            # a notification will wakeup the runner when a job finishes
            return wakeup_time
        if self._pause_until:
            # this channel is paused, request wakeup at the end of the pause
            if not wakeup_time:
                wakeup_time = self._pause_until
            else:
                wakeup_time = min(wakeup_time, self._pause_until)
            # since this channel is paused, no need to look at the
            # wakeup time of children nor eta jobs, as such jobs would not
            # run anyway because they would end up in this paused channel
            return wakeup_time
        wakeup_time = self._queue.get_wakeup_time(wakeup_time)
        for child in self.children.values():
            wakeup_time = child.get_wakeup_time(wakeup_time)
        return wakeup_time


class ChannelManager(object):
    """ High level interface for channels

    This class handles:

    * configuration of channels
    * high level api to create and remove jobs (notify, remove_job, remove_db)
    * get jobs to run

    Here is how the runner will use it.

    Let's create a channel manager and configure it.

    >>> from pprint import pprint as pp
    >>> cm = ChannelManager()
    >>> cm.simple_configure('root:4,A:4,B:1')
    >>> db = 'db'

    Add a few jobs in channel A with priority 10

    >>> cm.notify(db, 'A', 'A1', 1, 0, 10, None, 'pending')
    >>> cm.notify(db, 'A', 'A2', 2, 0, 10, None, 'pending')
    >>> cm.notify(db, 'A', 'A3', 3, 0, 10, None, 'pending')
    >>> cm.notify(db, 'A', 'A4', 4, 0, 10, None, 'pending')
    >>> cm.notify(db, 'A', 'A5', 5, 0, 10, None, 'pending')
    >>> cm.notify(db, 'A', 'A6', 6, 0, 10, None, 'pending')

    Add a few jobs in channel B with priority 5

    >>> cm.notify(db, 'B', 'B1', 1, 0, 5, None, 'pending')
    >>> cm.notify(db, 'B', 'B2', 2, 0, 5, None, 'pending')

    We must now run one job from queue B which has a capacity of 1
    and 3 jobs from queue A so the root channel capacity of 4 is filled.

    >>> pp(list(cm.get_jobs_to_run(now=100)))
    [<ChannelJob B1>, <ChannelJob A1>, <ChannelJob A2>, <ChannelJob A3>]

    Job A2 is done. Next job to run is A5, even if we have
    higher priority job in channel B, because channel B has a capacity of 1.

    >>> cm.notify(db, 'A', 'A2', 2, 0, 10, None, 'done')
    >>> pp(list(cm.get_jobs_to_run(now=100)))
    [<ChannelJob A4>]

    Job B1 is done. Next job to run is B2 because it has higher priority.

    >>> cm.notify(db, 'B', 'B1', 1, 0, 5, None, 'done')
    >>> pp(list(cm.get_jobs_to_run(now=100)))
    [<ChannelJob B2>]

    Let's say A1 is done and A6 gets a higher priority. A6 will run next.

    >>> cm.notify(db, 'A', 'A1', 1, 0, 10, None, 'done')
    >>> cm.notify(db, 'A', 'A6', 6, 0, 5, None, 'pending')
    >>> pp(list(cm.get_jobs_to_run(now=100)))
    [<ChannelJob A6>]

    Let's test the throttling mechanism. Configure a 2 seconds delay
    on channel A, end enqueue two jobs.

    >>> cm = ChannelManager()
    >>> cm.simple_configure('root:4,A:4:throttle=2')
    >>> cm.notify(db, 'A', 'A1', 1, 0, 10, None, 'pending')
    >>> cm.notify(db, 'A', 'A2', 2, 0, 10, None, 'pending')

    We have only one job to run, because of the throttle.

    >>> pp(list(cm.get_jobs_to_run(now=100)))
    [<ChannelJob A1>]
    >>> cm.get_wakeup_time()
    102

    We have no job to run, because of the throttle.

    >>> pp(list(cm.get_jobs_to_run(now=101)))
    []
    >>> cm.get_wakeup_time()
    102

    2 seconds later, we can run the other job (even though the first one
    is still running, because we have enough capacity).

    >>> pp(list(cm.get_jobs_to_run(now=102)))
    [<ChannelJob A2>]
    >>> cm.get_wakeup_time()
    104
    """

    def __init__(self):
        self._jobs_by_uuid = WeakValueDictionary()
        self._root_channel = Channel(name='root', parent=None, capacity=1)
        self._channels_by_name = WeakValueDictionary(root=self._root_channel)

    @classmethod
    def parse_simple_config(cls, config_string):
        """Parse a simple channels configuration string.

        The general form is as follow:
        channel(.subchannel)*(:capacity(:key(=value)?)*)?,...

        If capacity is absent, it defaults to 1.
        If a key is present without value, it gets True as value.
        When declaring subchannels, the root channel may be omitted
        (ie sub:4 is the same as root.sub:4).

        Returns a list of channel configuration dictionaries.

        >>> from pprint import pprint as pp
        >>> pp(ChannelManager.parse_simple_config('root:4'))
        [{'capacity': 4, 'name': 'root'}]
        >>> pp(ChannelManager.parse_simple_config('root:4,root.sub:2'))
        [{'capacity': 4, 'name': 'root'}, {'capacity': 2, 'name': 'root.sub'}]
        >>> pp(ChannelManager.parse_simple_config('root:4,root.sub:2:'
        ...                                       'sequential:k=v'))
        [{'capacity': 4, 'name': 'root'},
         {'capacity': 2, 'k': 'v', 'name': 'root.sub', 'sequential': True}]
        >>> pp(ChannelManager.parse_simple_config('root'))
        [{'capacity': 1, 'name': 'root'}]
        >>> pp(ChannelManager.parse_simple_config('sub:2'))
        [{'capacity': 2, 'name': 'sub'}]
        """
        res = []
        for channel_config_string in config_string.split(','):
            config = {}
            config_items = channel_config_string.split(':')
            name = config_items[0]
            if not name:
                raise ValueError('Invalid channel config %s: '
                                 'missing channel name' % config_string)
            config['name'] = name
            if len(config_items) > 1:
                capacity = config_items[1]
                try:
                    config['capacity'] = int(capacity)
                except:
                    raise ValueError('Invalid channel config %s: '
                                     'invalid capacity %s' %
                                     (config_string, capacity))
                for config_item in config_items[2:]:
                    kv = config_item.split('=')
                    if len(kv) == 1:
                        k, v = kv[0], True
                    elif len(kv) == 2:
                        k, v = kv
                    else:
                        raise ValueError('Invalid channel config %s: '
                                         'incorrect config item %s' %
                                         (config_string, config_item))
                    if k in config:
                        raise ValueError('Invalid channel config %s: '
                                         'duplicate key %s' %
                                         (config_string, k))
                    config[k] = v
            else:
                config['capacity'] = 1
            res.append(config)
        return res

    def simple_configure(self, config_string):
        """Configure the channel manager from a simple configuration string

        >>> cm = ChannelManager()
        >>> c = cm.get_channel_by_name('root')
        >>> c.capacity
        1
        >>> cm.simple_configure('root:4,autosub.sub:2')
        >>> cm.get_channel_by_name('root').capacity
        4
        >>> cm.get_channel_by_name('root.autosub').capacity
        >>> cm.get_channel_by_name('root.autosub.sub').capacity
        2
        >>> cm.get_channel_by_name('autosub.sub').capacity
        2
        """
        for config in ChannelManager.parse_simple_config(config_string):
            self.get_channel_from_config(config)

    def get_channel_from_config(self, config):
        """Return a Channel object from a parsed configuration.

        If the channel does not exist it is created.
        The configuration is applied on the channel before returning it.
        If some of the parent channels are missing when creating a subchannel,
        the parent channels are auto created with an infinite capacity
        (except for the root channel, which defaults to a capacity of 1
        when not configured explicity).
        """
        channel = self.get_channel_by_name(config['name'], autocreate=True)
        channel.configure(config)
        return channel

    def get_channel_by_name(self, channel_name, autocreate=False):
        """Return a Channel object by its name.

        If it does not exist and autocreate is True, it is created
        with a default configuration and inserted in the Channels structure.
        If autocreate is False and the channel does not exist, an exception
        is raised.

        >>> cm = ChannelManager()
        >>> c = cm.get_channel_by_name('root', autocreate=False)
        >>> c.name
        'root'
        >>> c.fullname
        'root'
        >>> c = cm.get_channel_by_name('root.sub', autocreate=True)
        >>> c.name
        'sub'
        >>> c.fullname
        'root.sub'
        >>> c = cm.get_channel_by_name('sub', autocreate=True)
        >>> c.name
        'sub'
        >>> c.fullname
        'root.sub'
        >>> c = cm.get_channel_by_name('autosub.sub', autocreate=True)
        >>> c.name
        'sub'
        >>> c.fullname
        'root.autosub.sub'
        >>> c = cm.get_channel_by_name(None)
        >>> c.fullname
        'root'
        >>> c = cm.get_channel_by_name('root.sub')
        >>> c.fullname
        'root.sub'
        >>> c = cm.get_channel_by_name('sub')
        >>> c.fullname
        'root.sub'
        """
        if not channel_name or channel_name == self._root_channel.name:
            return self._root_channel
        if not channel_name.startswith(self._root_channel.name + '.'):
            channel_name = self._root_channel.name + '.' + channel_name
        if channel_name in self._channels_by_name:
            return self._channels_by_name[channel_name]
        if not autocreate:
            raise ChannelNotFound('Channel %s not found' % channel_name)
        parent = self._root_channel
        for subchannel_name in channel_name.split('.')[1:]:
            subchannel = parent.get_subchannel_by_name(subchannel_name)
            if not subchannel:
                subchannel = Channel(subchannel_name, parent, capacity=None)
                self._channels_by_name[subchannel.fullname] = subchannel
            parent = subchannel
        return parent

    def notify(self, db_name, channel_name, uuid,
               seq, date_created, priority, eta, state):
        try:
            channel = self.get_channel_by_name(channel_name)
        except ChannelNotFound:
            _logger.warning('unknown channel %s, '
                            'using root channel for job %s',
                            channel_name, uuid)
            channel = self._root_channel
        job = self._jobs_by_uuid.get(uuid)
        if job:
            # db_name is invariant
            assert job.db_name == db_name
            # date_created is invariant
            assert job.date_created == date_created
            # if one of the job properties that influence
            # scheduling order has changed, we remove the job
            # from the queues and create a new job object
            if (seq != job.seq or
                    priority != job.priority or
                    eta != job.eta or
                    channel != job.channel):
                _logger.debug("job %s properties changed, rescheduling it",
                              uuid)
                self.remove_job(uuid)
                job = None
        if not job:
            job = ChannelJob(db_name, channel, uuid,
                             seq, date_created, priority, eta)
            self._jobs_by_uuid[uuid] = job
        # state transitions
        if not state or state == DONE:
            job.channel.set_done(job)
        elif state == PENDING:
            job.channel.set_pending(job)
        elif state in (ENQUEUED, STARTED):
            job.channel.set_running(job)
        elif state == FAILED:
            job.channel.set_failed(job)
        else:
            _logger.error("unexpected state %s for job %s", state, job)

    def remove_job(self, uuid):
        job = self._jobs_by_uuid.get(uuid)
        if job:
            job.channel.remove(job)
            del self._jobs_by_uuid[job.uuid]

    def remove_db(self, db_name):
        for job in self._jobs_by_uuid.values():
            if job.db_name == db_name:
                job.channel.remove(job)
                del self._jobs_by_uuid[job.uuid]

    def get_jobs_to_run(self, now):
        return self._root_channel.get_jobs_to_run(now)

    def get_wakeup_time(self):
        return self._root_channel.get_wakeup_time()
