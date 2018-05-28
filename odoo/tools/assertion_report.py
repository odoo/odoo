
class assertion_report(object):
    """
    Simple pair of success and failures counts (used to record XML
    `assert` tags as well as unittest tests outcome (in this case, not
    individual `assert`)).
    """
    def __init__(self):
        self.successes = 0
        self.failures = 0

    def record_success(self):
        self.successes += 1

    def record_failure(self):
        self.failures += 1

    def record_result(self, result):
        if result is None:
            pass
        elif result is True:
            self.record_success()
        elif result is False:
            self.record_failure()

    def __str__(self):
        res = 'Assertions report: %s successes, %s failures' % (self.successes, self.failures)
        return res
