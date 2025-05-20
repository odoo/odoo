import logging

import threading
from queue import Queue, Full

from odoo import api
from odoo.modules.registry import Registry
from odoo.service.server import CommonServer

_logger = logging.getLogger(__name__)


class Task:
    def __init__(self, func, env, *args, **kwargs):
        self.func = func
        self.env = env
        self.args = args
        self.kwargs = kwargs

class BackgroundTaskQueue(Queue[Task]):
    ...

class BackgroundTaskWorker(threading.Thread):
    """
    Background task to handle non-critical operations
    """

    def __init__(self, queue: BackgroundTaskQueue, id: int, max_error_count: int = 0):
        super().__init__(daemon=True, name=f'BackgroundTaskWorker-{id}')
        _logger.info("Starting %s", self.name)
        self._queue = queue
        self.max_error_count = max_error_count
        self.task_count = 0
        self.error_count = 0


    def loop(self):
        while not self.max_error_count or self.error_count < self.max_error_count:
            task = self._queue.get()
            try:
                db_registry = Registry(task.env["dbname"])
                with db_registry.cursor() as cr:
                    env = api.Environment(cr, task.env['uid'], task.env['context'])
                    task.func(task.env["self"].with_env(env), *task.args, **task.kwargs)
                self.task_count += 1
            except Exception as e:
                _logger.error(f"Error in background task: {e}")
                self.error_count += 1
            finally:
                self._queue.task_done()

    def run(self):
        self.loop()

class BackgroundTaskManager:
    def __init__(self, init_num_workers: int = 4, max_queue_size: int = 0, max_task_retries: int = 3):
        _logger.info("Initializing BackgroundTaskManager")
        self.max_task_retries = max_task_retries
        self._queue = BackgroundTaskQueue(maxsize=max_queue_size)
        self._workers = [BackgroundTaskWorker(self._queue, i) for i in range(init_num_workers)]
        for worker in self._workers:
            worker.start()

    def add_task(self, func, env, *args, **kwargs):
        task = Task(func, env, *args, **kwargs)

        @env["self"].env.cr.postcommit.add
        def add_task_after_commit():
            for _ in range(self.max_task_retries):
                try:
                    self._queue.put(task)
                except Full:
                    _logger.warning("Background task queue is full, retrying...")
                    continue
                break
        return task

    def add_worker(self):
        worker = BackgroundTaskWorker(self._queue, len(self._workers))
        self._workers.append(worker)
        worker.start()


    def get_workers(self):
        return self._workers

    def get_worker_stats(self):
        worker_stats = []
        for worker in self._workers:
            worker_stats.append({
                'name': worker.name,
                'task_count': worker.task_count,
                'error_count': worker.error_count,
            })
        return {
            "queue_size": self._queue.qsize(),
            'worker_count': len(self._workers),
            'worker_stats': worker_stats,
        }

    def remove_worker(self):
        if self._workers:
            worker = self._workers.pop()
            worker.join()

    def shutdown(self):
        _logger.info("Stopping BackgroundTaskWorkers")
        self._queue.join()


class BackgroundTaskManagerSingleton:
    def __init__(self):
        self._instance = BackgroundTaskManager(init_num_workers=4)

    def get_instance(self):
        return self._instance

def background_task(func):
    """Decorator to always run a function in the background.
    """

    def wrapper(self, *args, **kwargs):
        if "no_background" in kwargs:
            no_background = kwargs.pop("no_background")
        else:
            no_background = False
        if no_background:
            return func(self, *args, **kwargs)
        env = {
            'uid': self.env.uid,
            'context': self.env.context,
            'dbname': self.env.cr.dbname,
            'self': self,
        }

        task = background_task_manager.get_instance().add_task(func, env, *args, **kwargs)
        return task

    return wrapper

background_task_manager = BackgroundTaskManagerSingleton()
CommonServer.on_stop(background_task_manager.get_instance().shutdown)
