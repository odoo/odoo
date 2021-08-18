import time
from concurrent import futures

import grpc

from odoo import api, http
from odoo.cli import Command
from odoo.models import Model

protos, services = grpc.protos_and_services("odoo.addons.aumet.cli.products.proto")


def query():
    try:

        print(http)
        print(dir(http))
    except Exception as exc1:
        print(exc1)


class Products(services.ProductServicer):
    def consumeProduct(self, request, context):
        # print(http.request.env["product.template"])

        # consumer = RemoteConsumer()
        query()


        return protos.ProductReply(message='Hello, %s!RESTTTT' % request.name)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    services.add_ProductServicer_to_server(Products(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


