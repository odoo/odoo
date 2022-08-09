from contextlib import contextmanager
import logging
import marshal
import os
import reprlib

from ctypes import Structure, c_bool, c_int32, c_int64, c_ssize_t
from multiprocessing import Lock, RawValue, RawArray
from multiprocessing.shared_memory import SharedMemory
from statistics import mean, quantiles
from time import time, time_ns


_logger = logging.getLogger(__name__)


class SharedCacheStat:
    """ Statistic counters for cache entries. """
    __slots__ = (
        '_hit', '_miss', '_overwrite_same', '_overwrite_other',
        '_time_get', '_time_get_count', '_time_set', '_time_set_count', '_lock_time'
    )
    NB_TIME_SAVE = 100_000
    def __init__(self):
        self._hit = RawValue(c_int64, 0)
        self._miss = RawValue(c_int64, 0)
        self._overwrite_same = RawValue(c_int64, 0)  # Can happen if two worker check in the 'same' time if a key exist
        self._overwrite_other = RawValue(c_int64, 0)  # Shouldn't happen

        self._lock_time = Lock()
        self._time_get = RawArray(c_int64, [-1] * self.NB_TIME_SAVE)
        self._time_get_count = RawValue(c_int64, 0)
        self._time_set = RawArray(c_int64, [-1] * self.NB_TIME_SAVE)
        self._time_set_count = RawValue(c_int64, 0)

    def hit(self):
        self._hit.value += 1

    def miss(self):
        self._miss.value += 1

    def overwrite(self, same_value=True):
        if same_value:
            self._overwrite_same.value += 1
        else:
            self._overwrite_other.value += 1

    def ratio(self):
        return 100.0 * self._hit.value / (self._hit.value + self._miss.value or 1)

    @contextmanager
    def time_register_set(self):
        start = time_ns()
        yield
        end = time_ns() - start
        with self._lock_time:
            self._time_set[self._time_set_count.value % self.NB_TIME_SAVE] = end
            self._time_set_count.value += 1

    @contextmanager
    def time_register_get(self):
        start = time_ns()
        yield
        end = time_ns() - start
        with self._lock_time:
            self._time_get[self._time_get_count.value % self.NB_TIME_SAVE] = end
            self._time_get_count.value += 1

class ReadPreferringWriteLock:
    def __init__(self):
        self._read_counter = RawValue(c_int32, 0)
        self._read_counter_lock = Lock()
        self._write_lock = Lock()

    def _read_acquire(self):
        with self._read_counter_lock:
            self._read_counter.value += 1
            if self._read_counter.value == 1:
                self._write_lock.acquire()

    def _read_release(self):
        with self._read_counter_lock:
            self._read_counter.value -= 1
            if self._read_counter.value == 0:
                self._write_lock.release()

    def _write_available_acquire(self):
        return self._write_lock.acquire(block=False)

    def _write_acquire(self):
        self._write_lock.acquire()

    def _write_release(self):
        self._write_lock.release()

    @contextmanager
    def read_acquire(self):
        self._read_acquire()
        try:
            yield
        finally:
            self._read_release()

    def __enter__(self):
        # CRITICAL SPOT: if the process is killed after it acquired
        # but before setting the pid, the _lock is locked without knowing
        # which process took it, then the PreforkServer cannot release it.
        # See `force_release_if_mandatory` where there is a partial solution to this
        self._write_acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # CRITICAL SPOT: if the process is killed after resetting the pid
        # but before releasing, the _lock is locked without knowing
        # which process took it, then the PreforkServer cannot release it.
        # See `force_release_if_mandatory` where there is a partial solution for this
        try:
            self._write_release()
        except ValueError:
            # On the worst case of the worst case, if we have a ValueError ("release" an already released lock), it seems
            # that no other process has used the lock between (or it already finished)
            _logger.error("One process has release the lock when it was used.")
            raise Exception("One process has release the lock when it was used, it shouldn't happen")

    def force_release_if_mandatory(self, pid: int):
        """Release the lock if it is locked by the killed process with `pid`

        :param int pid: pid of a killed (mandatory) process
        """
        pass  # TODO: No recovery in RW lock

class _Entry(Structure):
    """
    Hash LRU Table entry structure
    """
    _fields_ = [
        ("hash", c_ssize_t),
        ("prev", c_int32),
        ("next", c_int32),
    ]

    def __str__(self) -> str:
        return f"hash={self.hash}, prev={self.prev}, next={self.next}"
    __repr__ = __str__

class _DataIndex(Structure):
    _fields_ = [
        ("position", c_int64),
        ("size", c_int64),  # TODO: maybe `end` instead, to avoid useless concat
    ]

    def __str__(self) -> str:
        return f"position={self.position}, size={self.size}"
    __repr__ = __str__

class SharedMemoryLRU:

    # Byte size allocate for each entry of data (key, value). A data entry can still take more space
    # but this value should match as good as possible the average size of data entry to avoid
    # losing too much memory (if too high) or losing too many entries (if too low)
    AVG_SIZE_OF_DATA = 20_000
    USABLE_FRACTION = 2 / 3  # USABLE_FRACTION is the maximum sm lru load (same as the max of python dict)

    def __init__(self, nb_entry: int):
        # TODO: AVG_SIZE_OF_DATA and Size of shared cache should be calculate from memory threehold by worker
        # and data
        """ Init a Shared Memory which acts as a dict with a lru.

        :param int nb_entry: number of entries in the hash table.
        :param int total_size: number of bytes take by the Shared Cache (20 MB by default)
        """
        byte_size = nb_entry * self.AVG_SIZE_OF_DATA
        _logger.info("Create Shared Memory of %d entries with %d bytes of data", nb_entry, byte_size)

        # The lock to ensure that only one process at a time can access the critical section
        self._lock = ReadPreferringWriteLock()
        # The Raw Shared Memory, will contain only data (key, value)
        self._sm = SharedMemory(size=byte_size, create=True)

        self._size = nb_entry

        # We cannot take more that 2 % of memory with one data (TODO ?)
        self._max_size_one_data = byte_size // 50
        # `self._max_length` should be always < than size.
        # bigger it is, more there are hash conflict, and then slow down the `_lookup` but decrease the memory cost
        self._max_length = int(nb_entry * self.USABLE_FRACTION)

        # root, length, free_len (see property below)
        self._head = RawArray(c_int32, [-1, 0, 1])
        # Hash and the linked list information for each entry index
        self._entry_table = RawArray(_Entry, [(0, -1, -1)] * nb_entry)
        # Position info of data for each entry index
        self._data_idx = RawArray(_DataIndex, [(-1, -1)] * nb_entry)
        # Position info of free memory blocks
        self._data_free = RawArray(_DataIndex, [(-1, -1)] * nb_entry)
        # Number of free memory block (max == size)
        self._data_free[0] = (0, self._sm.size)
        # Buffer of shared memory for data (key/value)
        self._data = self._sm.buf
        # Stat of the Shared Cache, should be call/modify inside the lock
        self._stats = SharedCacheStat()
        self._counter_should_touch = 0
        self._counter_touch = 0


    _root = property(lambda self: self._head[0], lambda self, x: self._head.__setitem__(0, x))
    _length = property(lambda self: self._head[1], lambda self, x: self._head.__setitem__(1, x))
    _free_len = property(lambda self: self._head[2], lambda self, x: self._head.__setitem__(2, x))

    def hook_process_killed(self, pid):
        """ Release the lock if it is locked by the killed process with `pid`

        :param int pid: pid of a killed (mandatory) process
        """
        self._lock.force_release_if_mandatory(pid)

    def is_alive(self):
        """ Check that the Shared Cache is still 'alive' """
        acquired = self._lock._write_lock.acquire(timeout=0.5)
        if acquired:
            self._lock._write_lock.release()
        return acquired

    def clear(self):
        """ Clear all the shared memory, shouldn't be use except for testing """
        with self._lock:
            self._clear()

    def print_stats(self):
        # 2022-07-01 13:34:01,090 44818 INFO master odoo.modules.shared_memory: Shared Cache counter statistics: 89.82322025800286 % (ratio), 1880 / 213 (hit / miss), Override: 0 (same value), 0 (other value)
        # 2022-07-01 13:34:01,099 44818 INFO master odoo.modules.shared_memory: Shared Cache data statistics: 213 items, mean = 15909.464788732394, min = 248, max = 134516, deciles = [993.2, 2945.6, 3638.6, 4832.8, 7238.0, 9687.2, 13671.4, 21661.2, 48140.4] bytes
        # 2022-07-01 13:34:01,104 44818 INFO master odoo.modules.shared_memory: Shared Cache time SET statistics: 213 items, mean = 0.1030, min = 0.0291, max = 0.4449, deciles = [0.040392, 0.0534256, 0.0676272, 0.07436580000000001, 0.081596, 0.0916602, 0.11676299999999999, 0.14191420000000002, 0.200109] ms
        # 2022-07-01 13:34:01,106 44818 INFO master odoo.modules.shared_memory: Shared Cache time GET statistics: 1880 items, mean = 0.1021, min = 0.0129, max = 0.9817, deciles = [0.0331003, 0.0409992, 0.047600699999999996, 0.05621620000000001, 0.06517150000000001, 0.07753360000000001, 0.09759169999999999, 0.1330932, 0.21779579999999998] ms
        with self._lock:
            _logger.info(
                "Shared Cache counter statistics: %.4f %% (ratio), %s / %s (hit / miss), Override: %s (same value), %s (other value)",
                self._stats.ratio(),
                self._stats._hit.value,
                self._stats._miss.value,
                self._stats._overwrite_same.value,
                self._stats._overwrite_other.value,
            )
            sizes = [data_id.size / 1_000_000 for data_id in self._data_idx if data_id.size != -1]
            if sizes:
                _logger.info(
                    "Shared Cache data statistics: %s items, %.2f %% used (%.2f MB / %.2f MB), mean = %.6f MB, min = %.6f MB, max = %.6f MB, deciles = %s MB",
                    len(sizes),
                    sum(sizes) * 100 / self._sm.size,
                    sum(sizes),
                    self._sm.size,
                    mean(sizes),
                    min(sizes),
                    max(sizes),
                    [f"{q:.6f}" for q in quantiles(sizes, n=10)],
                )
            with self._stats._lock_time:
                times_set = [t / 1_000_000 for t in self._stats._time_set if t != -1]  # In ms
                times_get = [t / 1_000_000 for t in self._stats._time_get if t != -1]  # In ms
                if times_set:
                    _logger.info(
                        "Shared Cache time SET statistics: %s items, mean = %.4f, min = %.4f, max = %.4f (i=%d), sum = %.4f, deciles = %s ms",
                        len(times_set),
                        mean(times_set),
                        min(times_set),
                        max(times_set),
                        times_set.index(max(times_set)),
                        sum(times_set),
                        [f"{q:.6f}" for q in quantiles(times_set, n=10)],
                    )
                if times_get:
                    _logger.info(
                        "Shared Cache time GET statistics: %s items, mean = %.4f, min = %.4f, max = %.4f (i=%d), sum = %.4f, deciles = %s ms",
                        len(times_get),
                        mean(times_get),
                        min(times_get),
                        max(times_get),
                        times_get.index(max(times_get)),
                        sum(times_get),
                        [f"{q:.6f}" for q in quantiles(times_get, n=10)],
                    )


    def _clear(self):
        """ Clear all the shared memory

        ! Need lock !
        """
        self._head[:] = [-1, 0, 1]
        self._entry_table[:] = [(0, -1, -1)] * self._size
        self._data_idx[:] = [(-1, -1)] * self._size
        self._data_free[0] = (0, self._sm.size)

    def _defrag(self):
        """
        Defragment the `self._data`, it will result in only one block of free fragment.
        The `self._entry_table` should already be up-to-date to avoid defragment

        O(log(n) * n), n is `self._max_length` (due to `sorted`)

        ! Need lock !
        """
        _logger.debug("Defragment the shared memory, nb fragment = %d", self._free_len)
        s = time()
        # Filtered out unused index and sorted by position to ensure that the defragmentation won't override any data
        current_position = 0
        used_indices = filter(lambda i: self._entry_table[i].prev != -1 and self._data_idx[i].position != -1, range(self._size))
        sorted_indexes = sorted(used_indices, key=lambda i: self._data_idx[i].position)
        for i in sorted_indexes:
            data_entry = self._data_idx[i]
            self._data[current_position:current_position + data_entry.size] = self._data[data_entry.position:data_entry.position + data_entry.size]
            data_entry.position = current_position
            current_position += data_entry.size
        self._data_free[0] = (current_position, self._sm.size - current_position)
        self._free_len = 1
        _logger.debug("Defragmented the shared memory in %.4f ms, remaining free space : %s", (time() - s), self._data_free[0])

    def _malloc(self, data):
        """
        Reserved a free slot of shared memory for the root entry,
        insert data into it and keep track of this spot.
        If there isn't enough memory, pop min(10% of entry, enough for this data) and _defrag

        ! Need lock !

        :param bytes data: (key, value) marshalled
        """
        size = len(data)
        nb_free_byte = 0
        for i in range(self._free_len):
            data_free_entry = self._data_free[i]
            if data_free_entry.size >= size:
                break
            nb_free_byte += data_free_entry.size
        else:
            if nb_free_byte < size:
                # If nb_free_byte isn't enough,
                # We pop existing data until we have enough memory
                for i in range(self._length):
                    if nb_free_byte >= size and i > self._length // 10:
                        # At minimum remove 10% of the memory to avoid too many defrag when available memory is the bottleneck
                        break
                    nb_free_byte += self._lru_pop()
                else:
                    raise MemoryError("Your max_size_one_data is > size_byte, it shouldn't happen")
                _logger.debug("Pop %s items to be handle to add the new item", i + 1)

            self._defrag()
            data_free_entry = self._data_free[0]

        mem_pos = data_free_entry.position
        self._data[mem_pos:(mem_pos + size)] = data
        # We restrict _malloc for the root entry only,
        # because an index can already change because of the lru_pop before
        self._data_idx[self._root] = (mem_pos, size)
        data_free_entry.size -= size
        data_free_entry.position += size

    def _free(self, index: int):
        """
        It is the opposite of _malloc. Free the memory used by entry at `index`
        Also, it launches sometime the _defrag if:
            - No more entry to register free position entry
            - The first free slot is too _small (heuristic: _small = AVG_SIZE_OF_DATA)

        ! Need lock !

        :param int index: entry index of the data to free
        """
        last = self._free_len
        self._data_free[last] = self._data_idx[index]
        free_size = self._data_free[last].size
        new_free_len = last + 1
        self._data_idx[index] = (-1, -1)
        # If the first free slot is too _small (heuristic: _small = AVG_SIZE_OF_DATA) and there are a lot of fragments to retrieve:
        # -> We should _defrag to get an efficient _malloc
        # Also _defrag directly if there isn't any place in self._data_free
        if (self._data_free[0].size < self.AVG_SIZE_OF_DATA and new_free_len > self._size // 10) or new_free_len >= self._size:
            # It will result that self._free_len == 1
            self._defrag()
        else:
            self._free_len = new_free_len

        return free_size  # Return the size freed

    def _lru_pop(self):
        """
        Remove the eldest entry/data used (approximately for now,
        because doesn't update lru if not acquire write lock)

        ! Need lock !
        """
        if self._root == -1:
            raise Exception(f"Try to pop from empty lru ({self._length})")
        prev_index = self._entry_table[self._root].prev
        return self._del_index(prev_index, self._entry_table[prev_index])

    def _del_index(self, index: int, entry: _Entry):
        """
        Remove the entry at `index` and data linked to.
        It compacts the hash table to ensure the correctness
        of the _lookup (linear probing)

        ! Need lock !

        :param int index: index of entry to delete
        :param _Entry index: entry to delete
        """
        if entry.prev == entry.next == index:  # If am the only one
            self._root = -1
        else:
            self._entry_table[entry.next].prev = entry.prev
            self._entry_table[entry.prev].next = entry.next
            if self._root == index:
                self._root = entry.next

        self._entry_table[index] = (0, -1, -1)
        self._length -= 1
        free_size = self._free(index)

        # Delete the keys that are between this element and the next free spot, having
        # an index lower or equal to the position we delete (conflicts handling).
        def move_index(old_index, new_index):
            old_entry = self._entry_table[old_index]
            hash_i, prev_i, next_i = old_entry.hash, old_entry.prev, old_entry.next
            if self._entry_table[old_index].next == old_index:  # if it is the only one item
                prev_i = next_i = new_index
            self._entry_table[prev_i].next = self._entry_table[next_i].prev = new_index
            self._entry_table[new_index] = (hash_i, prev_i, next_i)
            self._entry_table[old_index] = (0, -1, -1)
            self._data_idx[new_index] = self._data_idx[old_index]
            self._data_idx[old_index] = (-1, -1)
            if self._root == old_index:
                self._root = new_index

        index_empty = index
        for i in range(index + 1, index + self._size):
            i_mask = i % self._size  # from index -> self._size -> 0 -> index - 1
            i_entry = self._entry_table[i_mask]
            if i_entry.prev == -1:
                break
            hash_mask = i_entry.hash % self._size

            distance_i = i_mask - hash_mask if i_mask >= hash_mask else self._size - hash_mask + i_mask
            # distance error of i,
            # - if 0 then he is at the correct location don't move
            # - if < than distance_new = not suitable location
            # else compress
            if distance_i == 0:
                continue
            distance_new = index_empty - hash_mask if index_empty >= hash_mask else self._size - hash_mask + index_empty
            if distance_new < distance_i:
                move_index(i_mask, index_empty)
                index_empty = i_mask
        else:
            raise MemoryError("The hashtable seems full, there is an error in the shared memory management itself.")

        return free_size

    def _data_get(self, index: int):
        """
        Get (key, value) of entry at `index`.

        ! Need lock !
        """
        data_id = self._data_idx[index]
        # Load the value (not the key) outside the lock should be a good idea (for multi-processing performance).
        # But because it increases the complexity of data structure (need to have the key length)
        # and we are forced to copy the bytes outside the lock (or it can change between the release and the marshall.loads)
        # it isn't more efficient and increases the complexity of the code (need maybe more test) :/
        return marshal.loads(self._data[data_id.position:data_id.position + data_id.size])

    def _lookup(self, key, hash_: int) -> tuple:
        """
        Return the first (index, entry, value) corresponding to (key, hash).
        If a entry is found, the value is set else it is None.

        ! Need lock !
         """
        for i in range(self._size):
            index = (hash_ + i) % self._size
            entry = self._entry_table[index]
            if entry.prev == -1:
                return index, entry, None
            if entry.hash == hash_:
                key_full, val = self._data_get(index)
                if key_full == key:  # Hash conflict is rare, then it is ok to sometimes load too much.
                    return index, entry, val
        raise MemoryError("Hash table full, doesn't make any sense, LRU is broken")

    def __getitem__(self, key):
        """ Get a value from the key

        :param key: hashable key
        :raises KeyError: If the key doesn't exist
        :return: The value unmarshalled
        """
        with self._stats.time_register_get():
            hash_ = hash(key)
            with self._lock.read_acquire():
                index, entry, val = self._lookup(key, hash_)
                if val is None:
                    self._stats.miss()
                    raise KeyError(f"{key} does not exist")
                self._stats.hit()

                if self._root != index:
                    self._counter_should_touch += 1
                    with self._lock._read_counter_lock:
                        if self._lock._read_counter.value == 1:  # I have the write lock for myself and I lock _read_counter to avoid any intrusion
                            self._counter_touch += 1
                            # Pop me from my previous location
                            self._entry_table[entry.prev].next = entry.next
                            self._entry_table[entry.next].prev = entry.prev
                            # Put me in front
                            entry.next = self._root
                            entry.prev = self._entry_table[self._root].prev
                            self._entry_table[self._entry_table[self._root].prev].next = index
                            self._entry_table[self._root].prev = index
                            self._root = index
            if self._counter_should_touch == 2000:
                print(f"TOUCH : {self._counter_touch} on {self._counter_should_touch}")
            return val

    def __setitem__(self, key, value):
        with self._stats.time_register_set():
            hash_ = hash(key)
            data = marshal.dumps((key, value))
            if len(data) > self._max_size_one_data:
                raise MemoryError(f"The object of size {len(data)} is too large to put in the Shared Memory (max {self._max_size_one_data} bytes by entry)")

            with self._lock:
                index, entry, val = self._lookup(key, hash_)

                if val is not None:
                    self._stats.overwrite(val == value)
                    # TODO: Because we normally shouldn't override values (or with the same value), maybe we should return directly it we find a value
                    # Or we can compare it and return if it is the same ?

                if self._root == index:  # If I am already the root, just update the hash
                    self._entry_table[index].hash = hash_
                else:
                    if val is not None:  # Remove previous spot if exist
                        self._entry_table[entry.prev].next = entry.next
                        self._entry_table[entry.next].prev = entry.prev
                    if self._root == -1:  # First item set
                        self._entry_table[index] = (hash_, index, index)
                    else:
                        old_root_i = self._root
                        self._entry_table[index] = (hash_, self._entry_table[old_root_i].prev, old_root_i)
                        self._entry_table[self._entry_table[old_root_i].prev].next = index
                        self._entry_table[old_root_i].prev = index
                    self._root = index

                if val is None:
                    self._length += 1
                else:
                    self._free(index)
                self._malloc(data)  # Malloc use root entry to find index

                if self._length > self._max_length:
                    self._lru_pop()  # Make it after to avoid modifying index

    def __delitem__(self, key):
        hash_ = hash(key)
        with self._lock:
            index, entry, val = self._lookup(key, hash_)
            if val is None:
                raise KeyError(f"{key} doesn't not exist, cannot delete it")
            self._del_index(index, entry)

    # --------- Close methods

    def close(self):
        _logger.debug("Close shared memory")
        self._sm.close()

    def unlink(self):
        _logger.info("Unlink shared memory")
        self.close()
        del self._head, self._entry_table, self._data_idx, self._data_free, self._data, self._lock
        self._sm.unlink()
        del self

    # --------------------- TESTING methods ---------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unlink()

    def __len__(self):
        with self._lock:
            return self._length

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        return True

    # --------------------- DEBUGGING Methods --------------

    def __iter__(self):
        """ Only use for debugging"""
        # with self._lock:
        if self._root == -1:
            return
        node_index = self._root
        for _ in range(self._length + 1):
            yield self._data_get(node_index)
            node_index = self._entry_table[node_index].next
            if node_index == self._root:
                break
        else:
            raise MemoryError(f"Infinite loop detected in the Linked list, {self._root=}:\n" + "\n".join(str(i) + ": " + str(e) for i, e in enumerate(self._entry_table)))

    def __repr__(self) -> str:
        """ Only use for debugging"""
        result = []
        # with self._lock:
        if self._root == -1:
            return f'hashtable size: {self._size}, len: {str(self._length)}\n' + '\n'.join(result) + '\n' + "\n".join(str(e) for e in self._data_free[:self._free_len])
        node_index = self._root
        for _ in range(self._length + 1):
            hash_key, nxt = self._entry_table[node_index].hash, self._entry_table[node_index].next
            try:
                data = self._data_get(node_index)
            except (ValueError, EOFError):
                data = ("<unable to read>", "<unable to read>")
            result.append(f'key: {data[0]}, hash % size: {hash_key % self._size}, index: {node_index}, {self._entry_table[node_index]}, data_pos={self._data_idx[node_index].position} - data_size={self._data_idx[node_index].size}: {reprlib.repr(data[1])}')
            node_index = nxt
            if node_index == self._root:
                return f'hashtable size: {self._size}, len: {str(self._length)}, {self._root=}\n' + \
                    '\n'.join(result) + \
                    f'\nFree spots {self._free_len}:\n' + \
                    "\n".join(str(e) for e in self._data_free[:self._free_len])
        raise MemoryError(f"Infinite loop detected in the Linked list, {self._root=}:\n" + "\n".join(str(i) + ": " + str(e) for i, e in enumerate(self._entry_table)))
