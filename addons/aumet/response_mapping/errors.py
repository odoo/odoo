

class ErrorHelper:
    error = {
        "The payment method is not supported for this item": 409
    }
    @classmethod
    def get_status_code(cls,message):

        return (cls.error[message] if message in cls.error.keys() else False)


if  __name__ =="__main__":
    print(ErrorHelper.get_status_code("The payment method is not supported for this item"))