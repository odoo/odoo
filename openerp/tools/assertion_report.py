
class assertion_report(object):
    """
    Simple pair of success and failures counts (used to record YAML and XML
    `assert` tags as well as unittest2 tests outcome (in this case, not
    individual `assert`)).
    """
    def __init__(self):
        self.successes = 0
        self.failures = 0
        self.failures_details = []

    def record_success(self):
        self.successes += 1

    def record_failure(self, details=None):
        self.failures += 1
        if details is not None:
            self.failures_details.append(details)

    def record_result(self, result, details=None):
        """Record either success or failure, with the provided details in the latter case.

        :param result: a boolean
        :param details: a dict with keys ``'module'``, ``'testfile'``, ``'msg'``, ``'msg_args'``
        """
        if result is None:
            pass
        elif result is True:
            self.record_success()
        elif result is False:
            self.record_failure(details=details)

    def __str__(self):
        res = 'Assertions report: %s successes, %s failures' % (self.successes, self.failures)
        return res

