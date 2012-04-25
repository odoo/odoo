
function openerp_pos_devices(module, instance){ //module is instance.point_of_sale
    module.BarcodeReader = instance.web.Class.extend({
        init: function(attributes){
            this.pos = attributes.pos;
        },
        //returns true if the code is a valid EAN codebar number by checking the control digit.
        checkEan: function(code){
            var st1 = code.slice();
            var st2 = st1.slice(0,st1.length-1).reverse();
            // some EAN13 barcodes have a length of 12, as they start by 0
            while (st2.length < 12) {
                st2.push(0);
            }
            var countSt3 = 1;
            var st3 = 0;
            $.each(st2, function() {
                if (countSt3%2 === 1) {
                    st3 +=  this;
                }
                countSt3 ++;
            });
            st3 *= 3;
            var st4 = 0;
            var countSt4 = 1;
            $.each(st2, function() {
                if (countSt4%2 === 0) {
                    st4 += this;
                }
                countSt4 ++;
            });
            var st5 = st3 + st4;
            var cd = (10 - (st5%10)) % 10;
            return code[code.length-1] === cd;
        },
        // returns a product that has a packaging with an EAN matching to provided ean string. 
        // returns undefined if no such product is found.
        getProductByEAN: function(ean) {
            var allProducts = this.pos.get('product_list');
            var allPackages = this.pos.get('product.packaging');
            var prefix = ean.substring(0,2);
            var scannedProductModel = undefined;

            if (prefix in {'02':'', '22':'', '24':'', '26':'', '28':''}) {
            
                // PRICE barcode
                var itemCode = ean.substring(0,7);
                var scannedPackaging = _.detect(allPackages, function(pack) { return pack.ean !== undefined && pack.ean.substring(0,7) === itemCode;});
                if (scannedPackaging !== undefined) {
                    scannedProductModel = _.detect(allProducts, function(pc) { return pc.id === scannedPackaging.product_id[0];});
                    scannedProductModel.list_price = Number(ean.substring(7,12))/100;
                }
            } else if (prefix in {'21':'','23':'','27':'','29':'','25':''}) {
                // WEIGHT barcode
                var weight = Number(barcode.substring(7,12))/1000;
                var itemCode = ean.substring(0,7);
                var scannedPackaging = _.detect(allPackages, function(pack) { return pack.ean !== undefined && pack.ean.substring(0,7) === itemCode;});
                if (scannedPackaging !== undefined) {
                    scannedProductModel = _.detect(allProducts, function(pc) { return pc.id === scannedPackaging.product_id[0];});
                    scannedProductModel.list_price *= weight;
                    scannedProductModel.name += ' - ' + weight + ' Kg.';
                }
            } else {
                // UNIT barcode
                scannedProductModel = _.detect(allProducts, function(pc) { return pc.ean13 === ean;});   //TODO DOES NOT SCALE
            }
            return scannedProductModel;
        },
        //starts catching keyboard events and tries to interpret codebar 
        connect: function(){
            var self = this;
            var codeNumbers = [];
            var timeStamp = 0;
            var lastTimeStamp = 0;

            // The barcode readers acts as a keyboard, we catch all keyup events and try to find a 
            // barcode sequence in the typed keys, then act accordingly.
            $('body').delegate('','keyup', function (e){

                //We only care about numbers
                if (!isNaN(Number(String.fromCharCode(e.keyCode)))) {

                    // The barcode reader sends keystrokes with a specific interval.
                    // We look if the typed keys fit in the interval. 
                    if (codeNumbers.length==0) {
                        timeStamp = new Date().getTime();
                    } else {
                        if (lastTimeStamp + 30 < new Date().getTime()) {
                            // not a barcode reader
                            codeNumbers = [];
                            timeStamp = new Date().getTime();
                        }
                    }
                    codeNumbers.push(e.keyCode - 48);
                    lastTimeStamp = new Date().getTime();
                    if (codeNumbers.length == 13) {
                        //console.log('found code:', codeNumbers.join(''));

                        // a barcode reader
                        if (!self.checkEan(codeNumbers)) {
                            // barcode read error, raise warning
                            $(QWeb.render('pos-scan-warning')).dialog({
                                resizable: false,
                                height:220,
                                modal: true,
                                title: "Warning",
                            });
                        }
                        var selectedOrder = self.pos.get('selectedOrder');
                        var scannedProductModel = self.getProductByEAN(codeNumbers.join(''),allPackages,allProducts);
                        if (scannedProductModel === undefined) {
                            // product not recognized, raise warning
                            $(QWeb.render('pos-scan-warning')).dialog({
                                resizable: false,
                                height:220,
                                modal: true,
                                title: "Warning",
                                /*
                                buttons: {
                                    "OK": function() {
                                        $( this ).dialog( "close" );
                                        return;
                                    },
                                }*/
                            });
                        } else {
                            selectedOrder.addProduct(new module.Product(scannedProductModel));
                        }

                        codeNumbers = [];
                    }
                } else {
                    // NaN
                    codeNumbers = [];
                }
            });
        },
        disconnect: function(){
            $('body').undelegate('', 'keyup')
        },
    });
    
}
