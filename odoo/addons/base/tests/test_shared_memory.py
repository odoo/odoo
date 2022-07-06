import random
import string
import time
import itertools
import logging
from multiprocessing import Process
from threading import Thread
from typing import OrderedDict

from odoo.modules.shared_memory import SharedMemoryLRU, LockIdentify
from odoo.tests.common import BaseCase
from odoo.tools import mute_logger


_logger = logging.getLogger(__name__)


class TestLockPID(BaseCase):

    def test_lock_multiprocess_terminate(self):
        self.skipTest("Create a traceback impossible to mute")
        lock = LockIdentify()
        def sleeting():
            with lock:
                time.sleep(1)

        process = Process(target=sleeting)
        process.start()
        time.sleep(0.1)
        process.terminate()
        process.join()

        self.assertTrue(lock._lock.acquire(block=False), "Lock is not release when process is terminated")

    def test_lock_kill(self):
        # TODO mute the exception
        lock = LockIdentify()
        def sleeting():
            with lock:
                time.sleep(1)

        process = Process(target=sleeting)
        process.start()
        time.sleep(0.1)
        process.kill()
        process.join()

        lock.force_release_if_mandatory(process.pid)

        self.assertTrue(lock._lock.acquire(block=False), "Lock is not release when process is killed and force_release_if_mandatory")

class TestSharedMemoryLRU(BaseCase):

    def test_sm_basic_functionality(self):
        """ Test basic set/get feature of the SharedMemoryLRU """
        with SharedMemoryLRU(16) as lru:
            self.assertEqual(list(lru), [])
            lru["key"] = 10
            self.assertEqual(lru["key"], 10)
            with self.assertRaises(KeyError):
                lru["no exist"]

            del lru["key"]

            for i in range(lru._max_length):
                lru[i] = f"code_{i}"
                self.assertEqual(lru[i], f"code_{i}")

            lru[0]  # 0 index become the first of LRU

            lru[lru._max_length] = "code_8"
            lru[lru._max_length + 1] = "code_9"

            with self.assertRaises(KeyError):
                lru[1]  # Should be pop because of LRU
            with self.assertRaises(KeyError):
                lru[2]  # Should be pop because of LRU

            for i in range(3, lru._max_length + 2):
                del lru[i]
                with self.assertRaises(KeyError):
                    lru[i]
            del lru[0]

    def test_sm_datastructure_hashtable(self):
        """ Test internal structure of the SharedMemoryLRU """
        with SharedMemoryLRU(16) as lru:

            # TODO: hash of key == 0 doesn't work now
            lru[lru._size] = "test"  # hash & mask = 0, should be at index 0
            lru[1] = "other"  # hash & mask = 1 should be at index 1
            lru[lru._size * 2] = "test * 2"  # hash & mask = 0, should be at index 2

            del lru[1]

            # now lru._size * 2 should be in the index 1
            self.assertEqual(lru._entry_table[1].hash, lru._size * 2)
            self.assertEqual(lru[lru._size * 2], "test * 2")
            self.assertEqual(lru[lru._size], "test")
            self.assertEqual(list(lru), [(lru._size, "test"), (lru._size * 2, "test * 2")])

            lru[lru._size - 1] = "blu"  # hash & mask = 15 should be at index 15
            lru[(lru._size * 2) - 1] = "bla" # hash & mask = 15 (hash of 31) should be at index 2

            self.assertEqual(lru._entry_table[2].hash, 31, f"{lru._entry_table[lru._size - 1].hash} != {31}")
            self.assertEqual(lru[(lru._size * 2) - 1], "bla")
            self.assertEqual(lru[lru._size - 1], "blu")

            del lru[lru._size - 1]  # (lru._size * 2) - 1 should go at index 15

            self.assertEqual(lru[(lru._size * 2) - 1], "bla")
            self.assertEqual(lru._entry_table[2].hash, 0)
            self.assertEqual(lru._entry_table[15].hash, 31)
            self.assertEqual(lru._entry_table[1].hash, lru._size * 2, f"{lru._entry_table[1].hash} != {lru._size * 2}")
            self.assertEqual(lru[lru._size * 2], "test * 2")
            self.assertEqual(lru[lru._size], "test")

            # test lru
            self.assertEqual(list(lru), [(lru._size, "test"), (lru._size * 2, "test * 2"), ((lru._size * 2) - 1, "bla")])

    def test_sm_delete_1(self):
        """ Test the deletion (to ensure than _pop_lru() works correctly internally) of the SharedMemoryLRU """
        with SharedMemoryLRU(16) as lru:
            lru[lru._size] = "test0"  # index 0
            lru[lru._size * 2] = "test1"  # index 1
            lru[lru._size * 3] = "test2"  # index 2
            lru[1] = "test3"  # index 3
            lru[lru._size - 1] = "test15"  # index 15

            self.assertEqual(list(lru), [
                (lru._size - 1, "test15"),
                (1, "test3"),
                (lru._size * 3, "test2"),
                (lru._size * 2, "test1"),
                (lru._size, "test0"),
            ])

            del lru[lru._size * 2]
            self.assertEqual(list(lru), [
                (lru._size - 1, "test15"),
                (1, "test3"),
                (lru._size * 3, "test2"),
                (lru._size, "test0"),
            ])

            del lru[lru._size - 1]
            self.assertEqual(list(lru), [
                (1, "test3"),
                (lru._size * 3, "test2"),
                (lru._size, "test0"),
            ])

            del lru[lru._size]
            self.assertEqual(list(lru), [
                (1, "test3"),
                (lru._size * 3, "test2"),
            ])

            del lru[1]
            self.assertEqual(list(lru), [
                (lru._size * 3, "test2"),
            ])

            del lru[lru._size * 3]
            self.assertEqual(list(lru), [])

    def test_sm_delete_2(self):
        """ Test all possibility of deletion """
        size_lru = 16
        keys_values = {
            size_lru - 1: "h_mask 15 - index 15",
            (size_lru * 2) - 1: "h_mask 0 - index 0",
            1: "h_mask 1 - index 1",
            (size_lru * 3) - 1: "h_mask 0 - index 2",
            size_lru - 2: "h_mask 14 - index 14",
            (size_lru * 2) - 2: "h_mask 14 - index 3",
        }

        for keys in itertools.permutations(keys_values):
            with self.subTest(keys=keys), SharedMemoryLRU(size_lru) as lru:
                for key in keys:
                    lru[key] = keys_values[key]
                    self.assertEqual(lru[key], keys_values[key])

                for key in keys:
                    self.assertEqual(lru[key], keys_values[key])

                self.assertEqual(len(lru), len(keys))

                # check lru
                self.assertEqual(list(reversed([(k, keys_values[k]) for k in keys])), list(lru))

                for i, key in enumerate(keys):
                    del lru[key]
                    self.assertEqual(list(reversed([(k, keys_values[k]) for k in keys[i+1:]])), list(lru))

                self.assertEqual(len(lru), 0)

    def test_sm_pop_lru(self):
        """ Test _pop_lru of the SharedMemoryLRU """
        with SharedMemoryLRU(16) as lru:  # max_length for LRU == 8
            lru[lru._size] = "test0"  # index 0
            lru[lru._size * 2] = "test1"  # index 1
            lru[lru._size * 3] = "test2"  # index 2
            lru[1] = "test3"  # index 3
            lru[lru._size - 1] = "test15"  # index 15

            self.assertEqual(list(lru), [
                (lru._size - 1, "test15"),
                (1, "test3"),
                (lru._size * 3, "test2"),
                (lru._size * 2, "test1"),
                (lru._size, "test0"),
            ])

            lru._lru_pop()
            self.assertEqual(list(lru), [
                (lru._size - 1, "test15"),
                (1, "test3"),
                (lru._size * 3, "test2"),
                (lru._size * 2, "test1"),
            ])

            lru._lru_pop()
            self.assertEqual(list(lru), [
                (lru._size - 1, "test15"),
                (1, "test3"),
                (lru._size * 3, "test2"),
            ])

            lru._lru_pop()
            self.assertEqual(list(lru), [
                (lru._size - 1, "test15"),
                (1, "test3"),
            ])

            lru._lru_pop()
            self.assertEqual(list(lru), [
                (lru._size - 1, "test15"),
            ])

            lru._lru_pop()
            self.assertEqual(list(lru), [])

    def test_sm_datastructure_lru_1(self):
        """ Test the LRU feature of the SharedMemory """
        with SharedMemoryLRU(16) as lru:
            lru['a'] = "test_a"
            lru['b'] = "test_b"

            self.assertEqual(list(lru), [('b', "test_b"), ('a', "test_a")])
            lru['a']
            self.assertEqual(list(lru), [('a', "test_a"), ('b', "test_b")])
            lru['a']
            self.assertEqual(list(lru), [('a', "test_a"), ('b', "test_b")])
            lru['c'] = "test_c"
            self.assertEqual(list(lru), [('c', "test_c"), ('a', "test_a"), ('b', "test_b")])
            lru['d'] = "test_d"
            self.assertEqual(list(lru), [('d', "test_d"), ('c', "test_c"), ('a', "test_a"), ('b', "test_b")])

    def test_sm_datastructure_lru_2(self):
        with SharedMemoryLRU(16) as lru:
            lru['key1'] = 'test1'
            lru['key2'] = 'test2'
            self.assertEqual(lru['key2'], 'test2')
            lru['key2'] = 'test2'  # re-set the root
            self.assertEqual(list(lru), [('key2', 'test2'), ('key1', 'test1')])
            self.assertEqual(lru['key1'], 'test1')
            self.assertEqual(lru['key2'], 'test2')

    def test_sm_memory_exhausted(self):
        with SharedMemoryLRU(10) as lru:
            with mute_logger('odoo.service.shared_memory'):
                with self.assertRaises(MemoryError):
                    lru['test'] = "a" * lru._sm.size
            with self.assertRaises(KeyError):
                lru['test']
            self.assertEqual(lru._length, 0)

            with self.assertRaises(MemoryError):
                lru['test'] = "a" * lru._max_size_one_data

    def test_sm_free_data_coherence(self):
        random.seed(42)
        with SharedMemoryLRU(30) as lru:
            for i in range(5_000):
                key = str(i)
                value = (str(i) * random.randint(1, 2000))[:(lru._max_size_one_data - 20)]
                prev = OrderedDict(lru)
                lru[key] = value
                while len(prev) >= len(lru):
                    prev.popitem()
                prev[key] = value
                prev.move_to_end(key, False)
                self.assertEqual(len(lru), len(prev))
                self.assertEqual(len(lru), len(dict(lru)))
                self.assertEqual(len(dict(lru)), len(dict(prev)))
                self.assertEqual(dict(lru), dict(prev))

                # Test coherence between data entry and free data: no overlaps possible
                filter_sorted_indexes = sorted(filter(lambda i: lru._entry_table[i].prev != -1, range(lru._size)), key=lambda i: -lru._data_idx[i].position)
                free_sorted_indexes = sorted(range(lru._free_len), key=lambda i: -lru._data_free[i].position)
                data_entry = data_free = None
                while filter_sorted_indexes and free_sorted_indexes:
                    if not data_entry:
                        data_entry = lru._data_idx[filter_sorted_indexes.pop()]
                    if not data_free:
                        data_free = lru._data_free[free_sorted_indexes.pop()]

                    if data_free.size != 0 and (
                        (data_entry.position <= data_free.position and data_entry.position + data_entry.size > data_free.position)
                        or (data_entry.position > data_free.position and data_entry.position + data_entry.size < data_free.position)):
                        assert False, "Overlaps detected between data_free and data_idx"

                    if data_entry.position > data_free.position:
                        data_free = None
                    else:
                        data_entry = None

    def test_sm_long_run_1(self):
        random.seed(42)
        with SharedMemoryLRU(50) as lru:
            for i in range(5_000):
                if random.random() < 0.8 and lru._length > 1:
                    # read
                    index = random.randint(0, lru._length - 1)
                    prev = list(lru)[index]  # It is slow
                    self.assertEqual(lru[prev[0]], prev[1])
                else:
                    # write
                    key = str(i)
                    value = (str(i) * random.randint(1, 2000))[:(lru._max_size_one_data - 20)]
                    lru[key] = value
                    self.assertEqual(lru[key], value)

    def test_sm_long_run_2(self):
        random.seed("test_multi")

        with SharedMemoryLRU(5_000) as lru:
            for i in range(5_000):
                key = f'dbname_template_{i % 1500}'
                try:
                    if random.random() > 0.8:
                        raise KeyError()
                    lru[key]
                except KeyError:
                    lru[key] = (
                    f"""
                    <th class="text-left">
                        <strong>{key}</strong>
                    </th>
                    <div class="input-group">
                        <input type="number"
                            class="o_matrix_input"
                            t-att-ptav_ids="cell.ptav_ids"
                            t-att-value="cell.qty"/>
                    </div>
                    <span class="o_matrix_cell o_matrix_text_muted o_matrix_nocontent_container"> Not available </span>
                    def blabla():
                        return {key}
                    """ * random.randint(1, 1000))[:lru._max_size_one_data - len(key) - 20]

    def test_sm_multi_thread_long_run(self):
        nb_thread = 50
        operation_by_worker = 200

        random.seed("test_multi")

        def simulate_t_cache_usage(lru, prefix):
            for i in range(operation_by_worker):
                time.sleep(0.0001 * random.random())  # sleep 0-0.1 ms by operation
                key = f'dbname_template_{prefix}{i}'
                try:
                    lru[key]
                except KeyError:
                    time.sleep(0.0002 * random.random())  # sleep 0-0.2 ms by operation
                    lru[key] = (
                    f"""
                    <th class="text-left">
                        <strong>{key}</strong>
                    </th>
                    <div class="input-group">
                        <input type="number"
                            class="o_matrix_input"
                            t-att-ptav_ids="cell.ptav_ids"
                            t-att-value="cell.qty"/>
                    </div>
                    <span class="o_matrix_cell o_matrix_text_muted o_matrix_nocontent_container"> Not available </span>
                    def blabla():
                        return {key}
                    """ * random.randint(1, 200))[:lru._max_size_one_data - len(key) - 20]


        with SharedMemoryLRU(5_000) as lru:
            start = time.time()
            threads = [Thread(target=simulate_t_cache_usage, args=(lru, f"{i}")) for i in range(nb_thread)]
            for p in threads:
                p.start()
            for p in threads:
                p.join()
            _logger.info(
                "Simulate t-cache usage with %d Threads: %s ms by op (%s)", nb_thread,
                (time.time() - start) * 1000 / (operation_by_worker * nb_thread),
                (operation_by_worker * nb_thread)
            )

    def test_sm_multi_process_long_run(self):
        nb_process = 50
        operation_by_worker = 200

        random.seed("test_multi")

        def simulate_t_cache_usage(lru, prefix):
            for i in range(operation_by_worker):
                time.sleep(0.0001 * random.random())  # sleep 0-0.1 ms by operation
                key = f'dbname_template_{prefix}{i}'
                try:
                    lru[key]
                except KeyError:
                    time.sleep(0.0002 * random.random())  # sleep 0-0.2 ms by operation
                    lru[key] = (
                    f"""
                    <th class="text-left">
                        <strong>{key}</strong>
                    </th>
                    <div class="input-group">
                        <input type="number"
                            class="o_matrix_input"
                            t-att-ptav_ids="cell.ptav_ids"
                            t-att-value="cell.qty"/>
                    </div>
                    <span class="o_matrix_cell o_matrix_text_muted o_matrix_nocontent_container"> Not available </span>
                    def blabla():
                        return {key}
                    """ * random.randint(1, 200))[:lru._max_size_one_data - len(key) - 20]


        with SharedMemoryLRU(5_000) as lru:
            start = time.time()
            processes = [Process(target=simulate_t_cache_usage, args=(lru, f"{i}")) for i in range(nb_process)]
            for p in processes:
                p.start()
            for p in processes:
                p.join()
            _logger.info(
                "Simulate t-cache usage with %d Processes: %s ms by op (%s)", nb_process,
                (time.time() - start) * 1000 / (operation_by_worker * nb_process),
                (operation_by_worker * nb_process)
            )

    def test_sm_multi_process_coherence(self):

        def method_p1(lru):
            time.sleep(0.1)
            lru['test1'] = "abc"
            self.assertEqual(lru["test2"], "m2")

        def method_p2(lru):
            lru['test2'] = "m2"
            time.sleep(0.2)
            self.assertEqual(lru["test1"], "abc")

        with SharedMemoryLRU(10) as lru:
            process_1 = Process(target=method_p1, args=(lru,))
            process_2 = Process(target=method_p2, args=(lru,))
            process_1.start()
            process_2.start()
            process_1.join()
            process_2.join()
            self.assertEqual(lru["test1"], "abc")
            self.assertEqual(lru["test2"], "m2")

    @mute_logger('odoo.modules.shared_memory')
    def test_sm_multi_process_killed_long_run(self):
        """ Simulate "real" environment where some process is killed by the PreforkServer
        during the usage of SM
        """
        nb_process = 50
        operation_by_worker = 1000

        random.seed("test_multi")

        def simulate_usage(lru, prefix):
            for i in range(operation_by_worker):
                key = (f'dbname_template_{prefix}{i}', i)
                try:
                    lru[key]
                except KeyError:
                    lru[key] = (
                    f"""
                    <th class="text-left">
                        <strong>{key}</strong>
                    </th>
                    """,) * random.randint(1, 5)

        for _ in range(5):
            with SharedMemoryLRU(100) as lru:
                processes = [Process(target=simulate_usage, args=(lru, f"{i}")) for i in range(nb_process)]
                for p in processes:
                    p.start()

                for i, p in enumerate(random.sample(processes, len(processes))):
                    p.kill()
                    p.join()
                    lru.hook_process_killed(p.pid)
                    # Simulate server.py: if it cannot obtain the lock during some period of
                    # time, restart everything
                    if not lru.is_alive():
                        lru._lock._lock.release()
                    if i % (len(processes) // 5):
                        with lru._lock:
                            lru._check_consistence()
                            rep_lru = repr(lru)
                            self.assertFalse('<unable to read>' in rep_lru, rep_lru)

    def test_sm_multi_process_killed_consistent(self):
        """ Test that kill a process when it uses the SharedMemory doesn't let
        a deadlock it and that SharedMemory keeps the data structure coherent (Clean it)
        """

        class TestingSharedMemoryLRU(SharedMemoryLRU):
            def _malloc(self, data):
                if b'test2' in data:
                    time.sleep(10)  # Force to take more time to test the kill
                super()._malloc(data)

        def method_p1(lru):
            lru['test1'] = "abc" # Step 1
            time.sleep(0.1)
            lru['test2'] = "other" # Step 2, it will take 10 sec

        def method_p2(lru):
            lru['test3'] = "m3" # Step 1
            time.sleep(0.5)
            lru['test4'] = "m4" # Step 4

        with TestingSharedMemoryLRU(10) as lru:
            process_1 = Process(target=method_p1, args=(lru,))
            process_2 = Process(target=method_p2, args=(lru,))
            process_1.start()
            process_2.start()

            time.sleep(0.2)
            process_1.kill() # During the Step 2 of process_1 (Step 3)
            lru.hook_process_killed(process_1.pid)

            process_1.join()
            process_2.join()

            self.assertEqual(list(lru), [("test4", "m4")])
            self.assertEqual(lru["test4"], "m4")
            self.assertEqual(len(lru), 1)
            # The other value has be erase because process 1 has let the SM incoherent
            with self.assertRaises(KeyError):
                lru["test1"]
            with self.assertRaises(KeyError):
                lru["test2"]
            with self.assertRaises(KeyError):
                lru["test3"]

            # check that the SM still work
            for i in range(10):
                key, value = str(i), str(i) * 200
                lru[key] = value
                self.assertEqual(lru[key], value)

            with self.assertRaises(KeyError):
                lru["test4"]

    # ------------------- PERFORMANCE TESTING

    def test_performance_mono_process(self):

        with SharedMemoryLRU(4096 * 2) as lru:
            start = time.time()
            for i in range(lru._max_length):
                lru[str(i)] = i
            _logger.info(
                "Write without lru_pop: %s ms by write (%s)",
                (time.time() - start) * 1000 / lru._max_length, lru._max_length
            )

            start = time.time()
            for i in range(lru._max_length, lru._max_length * 2):
                lru[str(i)] = i
            _logger.info(
                "Write with lru_pop: %s ms by write (%s)",
                (time.time() - start) * 1000 / lru._max_length, lru._max_length
             )

            start = time.time()
            for i in range(lru._max_length, lru._max_length * 2):
                lru[str(i)]
            _logger.info(
                "Read (existing): %s ms by read (%s)",
                (time.time() - start) * 1000 / lru._max_length, lru._max_length
            )

            start = time.time()
            for i in range(lru._max_length, lru._max_length * 2):
                del lru[str(i)]
            _logger.info(
                "Delete (existing): %s ms by delete (%s)",
                (time.time() - start) * 1000 / lru._max_length, lru._max_length
            )

    def test_performance_multi_process(self):
        nb_process = 8
        nb_operation = 20_000

        def write_on_lru(lru, prefix, nb):
            for i in range(nb):
                lru[prefix + str(i)] = i

        def read_on_lru(lru, prefix, nb):
            for i in range(nb):
                lru[prefix + str(i)]

        def delete_on_lru(lru, prefix, nb):
            for i in range(nb):
                del lru[prefix + str(i)]

        with SharedMemoryLRU(int(nb_operation * (1 / SharedMemoryLRU.USABLE_FRACTION))) as lru:
            start = time.time()
            processes = [
                Process(target=write_on_lru, args=(lru, f"{i}_", lru._max_length // nb_process)) for i in range(nb_process)]
            for p in processes:
                p.start()
            for p in processes:
                p.join()
            _logger.info(
                "Write without lru_pop: %s ms by write (%s)",
                (time.time() - start) * 1000 / lru._max_length, lru._max_length
            )

            self.assertEqual(lru._length, lru._max_length)

            start = time.time()
            processes = [Process(target=write_on_lru, args=(lru, f"_{i}_", lru._max_length // nb_process)) for i in range(nb_process)]
            for p in processes:
                p.start()
            for p in processes:
                p.join()
            _logger.info(
                "Write with lru_pop: %s ms by write (%s)",
                (time.time() - start) * 1000 / lru._max_length, lru._max_length
            )

            self.assertEqual(lru._length, lru._max_length)

            start = time.time()
            processes = [Process(target=read_on_lru, args=(lru, f"_{i}_", lru._max_length // nb_process)) for i in range(nb_process)]
            for p in processes:
                p.start()
            for p in processes:
                p.join()
            _logger.info(
                "Read (existing): %s ms by read (%s)",
                (time.time() - start) * 1000 / lru._max_length, lru._max_length
            )

            self.assertEqual(lru._length, lru._max_length)

            start = time.time()
            processes = [Process(target=delete_on_lru, args=(lru, f"_{i}_", lru._max_length // nb_process)) for i in range(nb_process)]
            for p in processes:
                p.start()
            for p in processes:
                p.join()
            _logger.info(
                "Delete (existing): %s ms by delete (%s)",
                (time.time() - start) * 1000 / lru._max_length, lru._max_length
            )

            self.assertEqual(lru._length, 0)

    def test_performance_real_mono_process(self):
        # Size sample of t-cache template with demo data and website_sale
        size_sample = [
            65294, 13158, 8349, 10537, 9215, 765, 30940, 54101, 12340, 206964,
            28, 4149, 5826, 21940, 3252, 2184, 3707, 3447, 3746, 2156, 8610, 5271,
            12380, 3978, 18085, 4632, 5734, 4921,
        ]

        nb_write = 5_000
        nb_read = 100_000
        long_random_string = ''.join(random.choice(string.ascii_lowercase) for _ in range(max(size_sample) * 2))
        size_sample_i = [random.choice(size_sample) for _ in range(nb_write)]
        begin_sample_i = [random.randint(0, max(size_sample)) for _ in range(nb_write)]
        values = [
            ((f"dbname_template_blablabla_{i}", i), long_random_string[begin_sample_i[i]:begin_sample_i[i] + size_sample_i[i]])
            for i in range(nb_write)
        ]
        with SharedMemoryLRU(int(nb_write * (1 / SharedMemoryLRU.USABLE_FRACTION))) as lru:
            start = time.time()
            for _ in range(nb_write):
                key, value = random.choice(values)
                lru[key] = value
            _logger.info("Write with 'real' sample take %.4f ms by write in mono-process", (time.time() - start) * 1000 / nb_write)

            start = time.time()
            for _ in range(nb_read):
                key, _value = random.choice(values)
                try:
                    v = lru[key]
                    self.assertEqual(v, _value)
                except KeyError:
                    pass
            _logger.info("Read with 'real' sample take %.4f ms by read in mono-process", (time.time() - start) * 1000 / nb_read)

    def test_performance_real_multi_process(self):
        # Size sample of t-cache template with demo data and website_sale
        size_sample = [
            65294, 13158, 8349, 10537, 9215, 765, 30940, 54101, 12340, 206964,
            28, 4149, 5826, 21940, 3252, 2184, 3707, 3447, 3746, 2156, 8610, 5271,
            12380, 3978, 18085, 4632, 5734, 4921,
        ]

        nb_write = 5_000
        nb_read = 100_000
        nb_process = 20
        long_random_string = ''.join(random.choice(string.ascii_lowercase) for _ in range(max(size_sample) * 2))
        size_sample_i = [random.choice(size_sample) for _ in range(nb_write)]
        begin_sample_i = [random.randint(0, max(size_sample)) for _ in range(nb_write)]
        values = [
            ((f"dbname_template_blablabla_{i}", i), long_random_string[begin_sample_i[i]:begin_sample_i[i] + size_sample_i[i]])
            for i in range(nb_write)
        ]

        def write_on_lru(lru):
            for _ in range(nb_write // nb_process):
                key, value = random.choice(values)
                lru[key] = value

        def read_on_lru(lru):
            for _ in range(nb_read // nb_process):
                key, _value = random.choice(values)
                try:
                    v = lru[key]
                    self.assertEqual(v, _value)
                except KeyError:
                    pass

        with SharedMemoryLRU(int(nb_write * (1 / SharedMemoryLRU.USABLE_FRACTION))) as lru:
            start = time.time()
            processes = [Process(target=write_on_lru, args=(lru,)) for i in range(nb_process)]
            for p in processes:
                p.start()
            for p in processes:
                p.join()
            _logger.info(
                "Write with 'real' sample take %.4f ms by write in multi-process (%d)",
                (time.time() - start) * 1000 / nb_write, nb_process
            )

            start = time.time()
            processes = [Process(target=read_on_lru, args=(lru,)) for i in range(nb_process)]
            for p in processes:
                p.start()
            for p in processes:
                p.join()
            _logger.info(
                "Read with 'real' sample take %.4f ms by read in multi-process (%d)",
                (time.time() - start) * 1000 / nb_read, nb_process
            )
            # Check print stats
            lru.print_stats()

    @mute_logger('odoo.modules.shared_memory')
    def test_performance_reset_sm(self):
        with SharedMemoryLRU(5_000) as lru:
            start = time.time()
            nb_time = 100
            for _ in range(nb_time):
                lru._consistent.value = False
                lru._check_consistence()
            _logger.info("Reset Shared Memory of %d items take %.4f ms by reset", lru._size, (time.time() - start) * 1000 / nb_time)
