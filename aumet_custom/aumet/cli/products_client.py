import logging

import grpc.experimental

protos = grpc.protos("products.proto")
services = grpc.services("products.proto")

logging.basicConfig()

print(dir(services))
print(dir(services.Product))
response = services.Product.consumeProduct(protos.ProductRequest(name='you'),
                                     'localhost:50051',
                                     insecure=True)
print("Greeter client received: " + response.message)