db = openerp.init()

###
Local store access. Read once from localStorage upon construction and persist on every change.
There should only be one store active at any given time to ensure data consistency.
###
class Store
  constructor: ->
    store = localStorage['pos']
    @data = (store && JSON.parse store) || {}
  get: (key) ->
    @data[key]
  set: (key, value) ->
    @data[key] = value
    localStorage['pos'] = JSON.stringify @data

###
Gets all the necessary data from the OpenERP web client (session, shop data etc.)
###
class Pos
  constructor: ->
    @session.session_login 'web-trunk-pos', 'admin', 'admin', =>
      $.when(
        @fetch(
          'pos.category',
           ['name','parent_id','child_id']
        ),
        @fetch(
          'product.product',
          ['name','list_price','pos_categ_id','taxes_id','img'],
          [['pos_categ_id','!=','false']]
        ),
        @fetch(
          'account.bank.statement',
          ['account_id', 'currency', 'journal_id', 'state', 'name']
        ),
        @fetch(
          'account.journal',
          ['auto_cash', 'check_dtls', 'currency', 'name', 'type']
        )
      ).then @build_tree
  ready: $.Deferred()
  session: new db.base.Session 'DEBUG'
  store: new Store
  fetch: (osvModel, fields, domain, callback, errorCallback) ->
    callback = callback || (result) => @store.set osvModel, result
    dataSetSearch = new db.base.DataSetSearch this, osvModel, null, domain
    dataSetSearch.read_slice fields, 0, null, callback
  push: (osvModel, record, callback, errorCallback) ->
    dataSet = new db.base.DataSet(this, osvModel, null)
    dataSet.create record, callback, errorCallback
  categories: {}
  build_tree: =>
    for c in @store.get 'pos.category'
      @categories[c.id] = id:c.id, name:c.name, children:c.child_id,
      parent:c.parent_id[0], ancestors:[c.id], subtree:[c.id]
    for id, c of @categories
      @current_category = c
      @build_ancestors c.parent
      @build_subtree c
    @categories[0] =
      ancestors: []
      children: c.id for c in @store.get 'pos.category' when not c.parent_id[0]?
      subtree: c.id for c in @store.get 'pos.category'
    @ready.resolve()
  build_ancestors: (parent) ->
    if parent?
      @current_category.ancestors.unshift parent
      @build_ancestors @categories[parent].parent
  build_subtree: (category) ->
    for c in category.children
      @current_category.subtree.push c
      @build_subtree @categories[c]

window.pos = new Pos

$ ->
  $('#steps').buttonset() # jQuery UI buttonset

  ###
  ---
  Models
  ---
  ###

  class CashRegister extends Backbone.Model

  class CashRegisterCollection extends Backbone.Collection
    model: CashRegister

  class Product extends Backbone.Model

  class ProductCollection extends Backbone.Collection
    model: Product

  class Category extends Backbone.Model

  class CategoryCollection extends Backbone.Collection
    model: Category

  ###
  Each Order contains zero or more Orderlines (i.e. the content of the "shopping cart".)
  There should only ever be one Orderline per distinct product in an Order.
  To add more of the same product, just update the quantity accordingly.
  The Order also contains payment information.
  ###
  class Orderline extends Backbone.Model
    defaults: {
      quantity: 1,
      list_price: 0,
      discount: 0
    }
    incrementQuantity: -> @set quantity: (@get 'quantity') + 1
    getTotal: -> (@get 'quantity') * (@get 'list_price') * (1 - (@get 'discount')/100)
    exportAsJSON: ->
      result = {
        qty: (@get 'quantity'),
        price_unit: (@get 'list_price'),
        discount: (@get 'discount'),
        product_id: (@get 'id')
      }
      return result

  class OrderlineCollection extends Backbone.Collection
    model: Orderline

  ###
  Every PaymentLine has all the attributes of the corresponding CashRegister.
  ###
  class Paymentline extends Backbone.Model
    defaults: {
      amount: 0
    }
    getAmount: -> @get 'amount'
    exportAsJSON: ->
      result = {
        name: "Payment line",
        statement_id: (@get 'id'),
        account_id: (@get 'account_id')[0],
        journal_id: (@get 'journal_id')[0],
        amount: @getAmount()
      }
      return result

  class PaymentlineCollection extends Backbone.Collection
    model: Paymentline

  class Order extends Backbone.Model
    defaults: {
      validated: false
    }
    initialize: ->
      @set orderLines: new OrderlineCollection
      @set paymentLines: new PaymentlineCollection
      @set name: "Order " + @generateUniqueId()
    generateUniqueId: ->
      new Date().getTime()
    addProduct: (product) ->
      existing = (@get 'orderLines').get product.id
      if existing?
        existing.incrementQuantity()
      else
        (@get 'orderLines').add new Orderline product.toJSON()
    addPaymentLine: (cashRegister) ->
      newPaymentline = new Paymentline cashRegister
      ### TODO: Should be 0 for cash-like accounts ###
      newPaymentline.set amount: @getDueLeft()
      (@get 'paymentLines').add newPaymentline
    getName: ->
      return @get 'name'
    getTotal: ->
      return (@get 'orderLines').reduce ((sum, orderLine) -> sum + orderLine.getTotal()), 0
    getTotalTaxExcluded: ->
      return @getTotal()/1.21
    getTax: ->
      return @getTotal()/1.21*0.21
    getPaidTotal: ->
      return (@get 'paymentLines').reduce ((sum, paymentLine) -> sum + paymentLine.getAmount()), 0
    getChange: ->
      return @getPaidTotal() - @getTotal()
    getDueLeft: ->
      return @getTotal() - @getPaidTotal()
    exportAsJSON: ->
      orderLines = []
      (@get 'orderLines').each (item) => orderLines.push [0, 0, item.exportAsJSON()]
      paymentLines = []
      (@get 'paymentLines').each (item) => paymentLines.push [0, 0, item.exportAsJSON()]
      result = {
        name: @getName(),
        amount_paid: @getPaidTotal(),
        amount_total: @getTotal(),
        amount_tax: @getTax(),
        amount_return: @getChange(),
        lines: orderLines,
        statement_ids: paymentLines
      }
      return result

  class OrderCollection extends Backbone.Collection
    model: Order

  class Shop extends Backbone.Model
    defaults: {
      cashRegisters: (new CashRegisterCollection pos.store.get('account.bank.statement')),
      orders: new OrderCollection,
      products: new ProductCollection
    }
    initialize: ->
      (@get 'orders').bind 'remove', (removedOrder) =>
        if (@get 'orders').isEmpty()
          @addAndSelectOrder new Order
        if (@get 'selectedOrder') is removedOrder
          @set selectedOrder: (@get 'orders').last()
    addAndSelectOrder: (newOrder) ->
      (@get 'orders').add newOrder
      @set selectedOrder: newOrder


  ###
  The numpad handles both the choice of the property currently being modified
  (quantity, price or discount) and the edition of the corresponding numeric value.
  ###
  class NumpadState extends Backbone.Model
    defaults: {
      buffer: "0"
      mode: "quantity"
    }
    initialize: (options) ->
      @shop = options.shop
      @shop.bind 'change:selectedOrder', @reset, this
    appendNewChar: (newChar) ->
      oldBuffer = @get 'buffer'
      if oldBuffer is '0'
        @set buffer: newChar
      else if oldBuffer is '-0'
        @set buffer: "-" + newChar
      else
        @set buffer: (@get 'buffer') + newChar
      @updateTarget()
    deleteLastChar: ->
      tempNewBuffer = (@get 'buffer').slice(0, -1) || "0"
      if isNaN tempNewBuffer
        tempNewBuffer = "0"
      @set buffer: tempNewBuffer
      @updateTarget()
    switchSign: ->
      oldBuffer = @get 'buffer'
      @set buffer: if oldBuffer[0] is '-' then oldBuffer.substr 1 else "-" + oldBuffer
      @updateTarget()
    changeMode: (newMode) ->
      @set buffer: "0", mode: newMode
    reset: ->
      @set buffer: "0"
    updateTarget: ->
      bufferContent = @get 'buffer'
      if bufferContent && !isNaN bufferContent
        params = {}
        params[@get 'mode'] = parseFloat bufferContent
        (@shop.get 'selectedOrder').selected.set params

  ###
  ---
  Views
  ---
  ###

  class NumpadView extends Backbone.View
    initialize: (options) ->
      @state = options.state
    events: {
      'click button#numpad-backspace': 'clickDeleteLastChar',
      'click button#numpad-minus': 'clickSwitchSign',
      'click button.number-char': 'clickAppendNewChar',
      'click button.mode-button': 'clickChangeMode'
    }
    clickDeleteLastChar: ->
      @state.deleteLastChar()
    clickSwitchSign: ->
      @state.switchSign()
    clickAppendNewChar: (event) ->
      newChar = event.currentTarget.innerText
      @state.appendNewChar newChar
    clickChangeMode: (event) ->
      $('.selected-mode').removeClass 'selected-mode'
      $(event.currentTarget).addClass 'selected-mode'
      newMode = event.currentTarget.attributes['data-mode'].nodeValue
      @state.changeMode newMode

  ###
  Gives access to the payment methods (aka. 'cash registers')
  ###
  class PaypadView extends Backbone.View
    initialize: (options) ->
      @shop = options.shop
    events: {
      'click button': 'performPayment'
    }
    performPayment: (event) ->
      cashRegisterId = event.currentTarget.attributes['cash-register-id'].nodeValue
      cashRegisterCollection = (@shop.get 'cashRegisters')
      cashRegister = cashRegisterCollection.find (item) => (item.get 'id') is parseInt cashRegisterId, 10
      (@shop.get 'selectedOrder').addPaymentLine cashRegister
    render: ->
      $(@el).empty()
      (@shop.get 'cashRegisters').each (cashRegister) => $(@el).append (new PaymentButtonView model: cashRegister).render()

  class PaymentButtonView extends Backbone.View
    template: _.template $('#payment-button-template').html()
    render: ->
      $(@el).html @template {id: (@model.get 'id'), name: (@model.get 'journal_id')[1]}


  ###
  There are 3 steps in a POS workflow:
  1. prepare the order (i.e. chose products, quantities etc.)
  2. choose payment method(s) and amount(s)
  3. validae order and print receipt
  It should be possible to go back to any step as long as step 3 hasn't been completed.
  Modifying an order after validation shouldn't be allowed.
  ###
  class StepsView extends Backbone.View
    initialize: (options) ->
      @step = "products"
    events: {
      'click input.step-button': 'clickChangeStep'
    }
    clickChangeStep: (event) ->
      newStep = event.currentTarget.attributes['data-step'].nodeValue
      $('.step-screen').hide()
      $('#' + newStep + '-screen').show()
      @step = newStep

  ###
  Shopping carts.
  ###
  class OrderlineView extends Backbone.View
    tagName: 'tr'
    template: _.template $('#orderline-template').html()
    initialize: (options) ->
      @model.bind 'change', => $(@el).hide(); @render()
      @model.bind 'remove', => $(@el).remove()
      @order = options.order
      @numpadState = options.numpadState
    events: {
      'click': 'clickHandler'
    }
    clickHandler: ->
      @numpadState.reset()
      @select()
    render: ->
      @select()
      $(@el).html(@template @model.toJSON()).fadeIn 400, -> $('#current-order').scrollTop $(@).offset().top
    select: ->
      $('tr.selected').removeClass 'selected'
      $(@el).addClass 'selected'
      @order.selected = @model

  class OrderView extends Backbone.View
    initialize: (options) ->
      @shop = options.shop
      @numpadState = options.numpadState
      @shop.bind 'change:selectedOrder', @changeSelectedOrder, this
      @bindOrderLineEvents()
    changeSelectedOrder: ->
      @currentOrderLines.unbind()
      @bindOrderLineEvents()
      @render()
    bindOrderLineEvents: ->
      @currentOrderLines = (@shop.get 'selectedOrder' ).get 'orderLines'
      @currentOrderLines.bind 'add', @addLine, this
      @currentOrderLines.bind 'change', @render, this
      @currentOrderLines.bind 'remove', @render, this
    addLine: (newLine) ->
      $(@el).append (new OrderlineView model: newLine, order: (@shop.get 'selectedOrder'), numpadState: @numpadState).render()
      @updateSummary()
    render: ->
      $(@el).empty()
      @currentOrderLines.each (orderLine) =>
        $(@el).append (new OrderlineView model: orderLine, order: (@shop.get 'selectedOrder'), numpadState: @numpadState).render()
      @updateSummary()
    updateSummary: ->
      currentOrder = @shop.get 'selectedOrder'
      total = currentOrder.getTotal()
      totalTaxExcluded = currentOrder.getTotalTaxExcluded()
      tax = currentOrder.getTax()
      $('#subtotal').html(totalTaxExcluded.toFixed 2).hide().fadeIn()
      $('#tax').html(tax.toFixed 2).hide().fadeIn()
      $('#total').html(total.toFixed 2).hide().fadeIn()

  ###
  "Products" step.
  ###
  class CategoryView extends Backbone.View
    template: _.template $('#category-template').html()
    render: (ancestors, children) ->
      $(@el).html @template
        breadcrumb: pos.categories[c] for c in ancestors
        categories: pos.categories[c] for c in children

  class ProductView extends Backbone.View
    tagName: 'li'
    className: 'product'
    template: _.template $('#product-template').html()
    events: {
      'click a': 'addToOrder'
    }
    initialize: (options) ->
      @shop = options.shop
    addToOrder: (event) ->
      ### Preserve the category URL ###
      event.preventDefault()
      (@shop.get 'selectedOrder').addProduct @model
    render: ->
      $(@el).html @template @model.toJSON()

  class ProductListView extends Backbone.View
    tagName: 'ol'
    className: 'product-list'
    initialize: (options) ->
      @shop = options.shop
      (@shop.get 'products').bind 'reset', @render, this
    render: ->
      $(@el).empty()
      (@shop.get 'products').each (product) => $(@el).append (new ProductView model: product, shop: @shop).render()
      $('#products-screen').append @el

  ###
  "Payment" step.
  ###
  class PaymentlineView extends Backbone.View
    tagName: 'li'
    className: 'paymentline'
    template: _.template $('#paymentline-template').html()
    initialize: ->
      @model.bind 'change', @render, this
    events: {
      'keyup input': 'changeAmount'
    }
    changeAmount: (event) ->
      newAmount = event.currentTarget.value
      if newAmount && !isNaN(newAmount)
        @model.set amount: parseFloat(newAmount)
    render: ->
      $(@el).html @template {name: (@model.get 'journal_id')[1], amount: (@model.get 'amount')}

  class PaymentView extends Backbone.View
    initialize: (options) ->
      @shop = options.shop
      @shop.bind 'change:selectedOrder', @changeSelectedOrder, this
      @bindPaymentLineEvents()
      @bindOrderLineEvents()
    paymentLineList: ->
      $(@el).find '#paymentlines'
    events: {
      'click button#validate-order': 'validateCurrentOrder'
    }
    validateCurrentOrder: ->
      currentOrder = @shop.get 'selectedOrder'
      callback = => currentOrder.set validated: true
      pos.push 'pos.order', currentOrder.exportAsJSON(), callback
    bindPaymentLineEvents: ->
      @currentPaymentLines = (@shop.get 'selectedOrder').get 'paymentLines'
      @currentPaymentLines.bind 'add', @addPaymentLine, this
      @currentPaymentLines.bind 'change', @render, this
      @currentPaymentLines.bind 'remove', @render, this
      @currentPaymentLines.bind 'all', @updatePaymentSummary, this
    bindOrderLineEvents: ->
      @currentOrderLines = (@shop.get 'selectedOrder').get 'orderLines'
      @currentOrderLines.bind 'all', @updatePaymentSummary, this
    changeSelectedOrder: ->
      @currentPaymentLines.unbind()
      @bindPaymentLineEvents()
      @currentOrderLines.unbind()
      @bindOrderLineEvents()
      @render()
    addPaymentLine: (newPaymentLine) ->
      @paymentLineList().append (new PaymentlineView model: newPaymentLine).render()
    render: ->
      @paymentLineList().empty()
      @currentPaymentLines.each (paymentLine) => @paymentLineList().append (new PaymentlineView model: paymentLine).render()
      @updatePaymentSummary()
    updatePaymentSummary: ->
      currentOrder = @shop.get 'selectedOrder'
      paidTotal = currentOrder.getPaidTotal()
      dueTotal = currentOrder.getTotal()
      $(@el).find('#payment-due-total').html dueTotal.toFixed 2
      $(@el).find('#payment-paid-total').html paidTotal.toFixed 2
      remainingAmount = dueTotal-paidTotal
      remaining = if remainingAmount > 0 then "Due left: " + remainingAmount.toFixed 2 else "Change: " + (-remainingAmount).toFixed 2
      $('#payment-remaining').html remaining

  ###
  "Receipt" step.
  ###
  class ReceiptLineView extends Backbone.View
    tagName: 'li'
    className: 'receiptline'
    template: _.template $('#receiptline-template').html()
    initialize: ->
      @model.bind 'change', @render, this
    render: ->
      $(@el).html @template @model.toJSON()

  class ReceiptView extends Backbone.View
    initialize: (options) ->
      @shop = options.shop
      @shop.bind 'change:selectedOrder', @changeSelectedOrder, this
      @bindOrderLineEvents()
      @bindPaymentLineEvents()
    receiptLineList: ->
      $(@el).find('#receiptlines')
    bindOrderLineEvents: ->
      @currentOrderLines = (@shop.get 'selectedOrder').get 'orderLines'
      @currentOrderLines.bind 'add', @addReceiptLine, this
      @currentOrderLines.bind 'change', @render, this
      @currentOrderLines.bind 'remove', @render, this
    bindPaymentLineEvents: ->
      @currentPaymentLines = (@shop.get 'selectedOrder').get 'paymentLines'
      @currentPaymentLines.bind 'all', @updateReceiptSummary, this
    changeSelectedOrder: ->
      @currentOrderLines.unbind()
      @bindOrderLineEvents()
      @currentPaymentLines.unbind()
      @bindPaymentLineEvents()
      @render()
    addReceiptLine: (newOrderItem) ->
      @receiptLineList().append (new ReceiptLineView model: newOrderItem).render()
      @updateReceiptSummary()
    render: ->
      @receiptLineList().empty()
      @currentOrderLines.each (orderItem) => @receiptLineList().append (new ReceiptLineView model: orderItem).render()
      @updateReceiptSummary()
    updateReceiptSummary: ->
      currentOrder = @shop.get 'selectedOrder'
      total = currentOrder.getTotal()
      tax = currentOrder.getTax()
      change = currentOrder.getPaidTotal() - total
      $('#receipt-summary-tax').html tax.toFixed 2
      $('#receipt-summary-total').html total.toFixed 2
      $('#receipt-summary-change').html change.toFixed 2

  class OrderButtonView extends Backbone.View
    tagName: 'li'
    className: 'order-selector-button'
    template: _.template $('#order-selector-button-template').html()
    initialize: (options) ->
      @order = options.order
      @shop = options.shop
      @order.bind 'destroy', => $(@el).remove()
      @shop.bind 'change:selectedOrder', (shop) =>
        selectedOrder = shop.get 'selectedOrder'
        if @order is selectedOrder
          @setButtonSelected()
    events: {
      'click button.select-order': 'selectOrder',
      'click button.close-order': 'closeOrder'
    }
    selectOrder: (event) ->
      @shop.set selectedOrder: @order
    setButtonSelected: ->
      $('.selected-order').removeClass 'selected-order'
      $(@el).addClass 'selected-order'
    closeOrder: (event) ->
      @order.destroy()
    render: ->
      $(@el).html @template @order.toJSON()

  class ShopView extends Backbone.View
    initialize: (options) ->
      @shop = options.shop
      (@shop.get 'orders').bind 'add', @orderAdded, this
      (@shop.get 'orders').add new Order
      @numpadState = new NumpadState
        shop: @shop
      @productListView = new ProductListView
        shop: @shop
      @paypadView = new PaypadView
        shop: @shop
        el: $('#paypad')
      @paypadView.render()
      @orderView = new OrderView
        shop: @shop,
        numpadState: @numpadState
        el: $('#current-order-content')
      @paymentView = new PaymentView
        shop: @shop,
        el: $('#payment-screen')
      @receiptView = new ReceiptView
        shop: @shop,
        el: $('#receipt-screen')
      @numpadView = new NumpadView
        state: @numpadState,
        el: $('#numpad')
      @stepsView = new StepsView
        el: $('#steps')
    events: {
      'click button#neworder-button': 'createNewOrder'
    }
    createNewOrder: ->
      newOrder = new Order
      (@shop.get 'orders').add newOrder
      @shop.set selectedOrder: newOrder
    orderAdded: (newOrder) ->
      newOrderButton = new OrderButtonView
        order: newOrder,
        shop: @shop
      $('#orders').append (newOrderButton).render()
      newOrderButton.selectOrder()

  class App extends Backbone.Router
    routes:
      '': 'category'
      'category/:id': 'category'
    initialize: ->
      @shop = new Shop
      @shopView = new ShopView
        shop: @shop
        el: $('body')
      @categoryView = new CategoryView
    category: (id = 0) ->
      c = pos.categories[id]
      $('#products-screen').html(@categoryView.render c.ancestors, c.children)
      products = pos.store.get('product.product').filter (p) -> p.pos_categ_id[0] in c.subtree
      (@shop.get 'products').reset products
      $('.searchbox input').keyup ->
        s = $(@).val().toLowerCase()
        if s
          m = products.filter (p) -> p.name.toLowerCase().indexOf s
          $('.search-clear').fadeIn()
        else
          m = products
          $('.search-clear').fadeOut()
        (@shop.get 'products').reset m
      $('.search-clear').click ->
        (@shop.get 'products').reset products
        $('.searchbox input').val('').focus()
        $('.search-clear').fadeOut()

  pos.ready.then ->
    pos.app = new App
    Backbone.history.start()
