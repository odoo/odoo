# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from concurrent.futures import Future, wait, FIRST_COMPLETED
import inspect
import sys


def execute_callable_from_generator(generator_or_lst, executor=None):
    """Iter the generators on the main thread while executing the yielded callable on the executor.

    The goal is to execute a list of function in "parallel" (coroutines) on the MAIN thread while allowing each function
    to execute long process (ex.: a request) on the executor (i.e. not in the main thread if executor is not None).
    Thanks to that, each function is executed sequentially AND everything except the yielded callables are executed on
    the MAIN thread.

    Example of usage:
    def long_running_method_with_no_odoo_dependency_inc_1(param):
        sleep(10)
        return param + 1

    def gen_inc_2(init):
        res = (yield lambda: long_running_method_with_no_odoo_dependency_inc_1(init)).result()
        res = (yield lambda: long_running_method_with_no_odoo_dependency_inc_1(res)).result()
        yield res

    with ThreadPoolExecutor(max_workers=2) as executor:
        start_time = timeit.default_timer()
        results = [res.result() for res in execute_callable_from_generator([gen_inc_2(0), gen_inc_2(1)], executor)]
        print(f'Elapsed : {timeit.default_timer() - start_time}s')
        print(results)

    --> Elapsed: 20.02s
    [2, 3]
    Remarks:
    - execute in 20s instead of 40s and gives [0 + 2, 1 + 2].
    - gen_inc_2 is executed on MAIN thread while long_running_method_with_no_odoo_dependency_inc_1 is executed by the
    executor (on one of the 2 thread of the pool)

    :param generator_or_lst: either a single generator or a list of generator
    :param executor: an executor
    :return: for each generator returns the last non-callable yielded value or None if there are None.
    if generator_or_lst is a list, return the return value of each generator in the order of the generator
    if  generator_or_lst is a single generator, return the return value of the generator
    """
    if isinstance(generator_or_lst, list):
        generators = generator_or_lst
    else:
        generators = [generator_or_lst]

    if not all(inspect.isgenerator(generator) for generator in generators):
        raise Exception('Invalid parameter (at least one is not a generator)')

    def build_future(result=None, exception=None):
        ret = Future()
        if exception:
            ret.set_exception(exception.with_traceback(sys.exc_info()[2]))
        else:
            ret.set_result(result)
        return ret

    def submit_task(a_task):
        if executor:
            return executor.submit(a_task)
        try:
            return build_future(a_task())
        except Exception as e:
            return build_future(exception=e)

    def get_tasks_done(task_lst):
        if executor:
            tasks_done, _ = wait(task_lst, return_when=FIRST_COMPLETED)
            return tasks_done
        return task_lst

    results = [None for _ in range(len(generators))]
    pending_task_info = {}

    def send_to_generator(gen_idx, operation, send_value=False):
        next_task_fun = None
        generator = generators[gen_idx]
        try:
            next_task_fun = generator.send(operation.result() if send_value else operation)
        except StopIteration:
            results[gen_idx] = build_future()
        except Exception as e:
            results[gen_idx] = build_future(exception=e)
        else:
            if not callable(next_task_fun):
                results[gen_idx] = build_future(next_task_fun)
                next_task_fun = None
                too_many_items = False
                while True:  # exhaust generator
                    try:
                        generator.send(None)
                    except StopIteration:
                        break
                    else:
                        too_many_items = True
                if too_many_items:
                    raise Exception('Not callable yielded while generator not depleted')
        if next_task_fun:
            next_task = submit_task(next_task_fun)
            pending_task_info[id(next_task)] = (gen_idx, next_task)

    for i in range(len(generators)):
        send_to_generator(i, build_future(None), send_value=True)

    while pending_task_info:
        for task in get_tasks_done([pending_op for _, pending_op in pending_task_info.values()]):
            gen_i, _ = pending_task_info.pop(id(task))
            send_to_generator(gen_i, task)

    if isinstance(generator_or_lst, list):
        return results
    return results[0]


def execute_callable_from_sub_generator(generator, ret_value_lst):
    """Helper to retransmit callable to execute from a sub generator called with execute_callable_from_generator.

    Example of usage:
    def long_running_method_with_no_odoo_dependency_inc_1(param):
        sleep(10)
        return param + 1

    def sub_gen_inc_2(init):
        res = (yield lambda: long_running_method_with_no_odoo_dependency_inc_1(init)).result()
        res += 1
        yield res

    def gen_inc_3(init):
        res = (yield lambda: long_running_method_with_no_odoo_dependency_inc_1(init)).result()
        res2 = []
        yield from execute_callable_from_sub_generator(sub_gen_inc_2(res), res2)
        yield res2[0]

    with ThreadPoolExecutor(max_workers=2) as executor:
        start_time = timeit.default_timer()
        results = [res.result() for res in execute_callable_from_generator([gen_inc_3(0), gen_inc_3(1)], executor)]
        print(f'Elapsed : {timeit.default_timer() - start_time}s')
        print(results)

    --> Elapsed: 20.02s
    [3, 4]
    Remarks:
    - execute in 20s instead of 40s and gives [0 + 3, 1 + 3]
    - gen_inc_2 and sub_gen_inc_2 are executed on MAIN thread while long_running_method_with_no_odoo_dependency_inc_1
    is executed by the executor (on one of the 2 thread of the pool)

    :param generator: generator that yields callable to be executed by an upstream executor
    :param ret_value_lst: list where last non-callable yielded value will be appended. It allows to the generator
    function to return a value (beside the task to be executed)
    """
    if not inspect.isgenerator(generator):
        raise Exception('Invalid parameter (not a generator)')
    last_result = None
    while True:
        try:
            next_op = generator.send(last_result)
            if callable(next_op):
                last_result = yield next_op
            else:
                ret_value_lst.append(next_op)
                too_many_items = False
                while True:  # exhaust generator
                    try:
                        generator.send(None)
                    except StopIteration:
                        break
                    else:
                        too_many_items = True
                if too_many_items:
                    raise Exception('Not callable yielded while generator not depleted')
                break
        except StopIteration:
            ret_value_lst.append(None)
            break
