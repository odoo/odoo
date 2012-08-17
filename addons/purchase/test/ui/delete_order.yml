-
  In order to test to delete process on purchase order.
-
  I try to delete confirmed order and check Error Message.
-
  !python {model: purchase.order}: |
    try:
        self.unlink(cr, uid, [ref("purchase_order_1")])
    except Exception,e:
        pass
-
  I delete a draft order.
-
  !python {model: purchase.order}: |
    self.unlink(cr, uid, [ref("purchase_order_5")])
-
  I delete a cancelled order.
-
  !python {model: purchase.order}: |
    self.unlink(cr, uid, [ref("purchase_order_7")])


