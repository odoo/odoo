

class ErrorHelper:
    error = {
        "The payment method is not supported for this item": 409
    }
    @classmethod
    def get_status_code(cls,message):

        return (cls.error[message] if message in cls.error.keys() else False)
