
function actions(data, type, full) {
    return '<div class="nowrap-td">' +
        Dandelion.actionButtonSpecific('Taisyti', 'blue edit', full.id,
            'data-loaned-qty="' + full.loanedQty + '"') +
        Dandelion.actionButton('Išduoti', 'red loan', full) +
        Dandelion.actionButton('Grąžinti', 'green return', full) +
        Dandelion.actionButtonSpecific('Nurašyti', 'red writeoff', full.id,
            'data-loaned-qty="' + full.loanedQty + '"');
        '</div>';
}

function verify(data, type, full) {
    return data == true ?
        Dandelion.actionButton('Taip', 'green verify-remove', full) :
        Dandelion.actionButton('Ne', 'red verify', full);
}

$(function () {
    var reservationTable = $('#reservation-table');
    var returnModal = $('#return-modal');
    var editModal = $('#edit-modal');
    var writeoffModal = $('#writeoff-modal');

    reservationTable.on('click', 'a.verify', function () {
        action(this, 'verify');
    });

    reservationTable.on('click', 'a.verify-remove', function () {
        action(this, 'un-verify');
    });

    function action(object, action) {
        var id = $(object).data('id');
        console.log();
        $.post(app.fullPath('reservation/verify/' + id + '?action=' + action), null, function () {
            location.reload();
        });
    }

    var reservationId = null;
    reservationTable.on('click', 'a.loan', function () {
        reservationId = $(this).data('id');
        reservedQty = $(this).data('reserved-qty');
        console.log(reservedQty);
        $.ajax({
            type: "POST",
            url: 'reservation/' + reservationId + '/loan',
            success: function () {
                toastr.success('Knygos sėkmingai išduotos');
                Dandelion.reload('#reload');
            },
            error: function () {
                toastr.error('Nepavyko išduoti knygų');
            }
        });
    });

    reservationTable.on('click', 'a.return', function () {
        id = $(this).data('id');
        returnModal.modal();
    });


    returnModal.find('form').submit(function (e) {
        var formData = Mvs.formToObject(this);
        var returnQty = $('#return-qty').val();
        $.ajax({
            type: "POST",
            url: '/reservation/' + id + '/return/' + returnQty,
            data: JSON.stringify(formData),
            contentType: "application/json;charset=UTF-8",
            dataType: 'json',
            success: function () {
                toastr.success('Vadovėliai grąžinti');
                Dandelion.reload('#reload');
                returnModal.modal('hide');
            },
            error: function () {
                toastr.error('Nepavyko grąžinti vadovėlių');
            }
        });
        e.preventDefault();
    });

    reservationTable.on('click', 'a.edit', function () {
        id = $(this).data('id');
        var loanedQty = $(this).data('loaned-qty');
        console.log(loanedQty);
        if (loanedQty === 0 ){
            editModal.modal();
        }else{
            toastr.error("Vadovėliai jau išduoti, taisyti negalima");
        }

    });

    editModal.find('form').submit(function (e) {
        var formData = Mvs.formToObject(this);
        var editQty = $('#edit-qty').val();
        $.ajax({
            type: "POST",
            url: '/reservation/' + id + '/edit/' + editQty,
            data: JSON.stringify(formData),
            contentType: "application/json;charset=UTF-8",
            dataType: 'json',
            success: function () {
                toastr.success('Rezervacija pataisyta');
                Dandelion.reload('#reload');
                editModal.modal('hide');
            },
            error: function () {
                toastr.error('Nepavyko pataisyt rezervacijos');
            }
        });
        e.preventDefault();
    });

    var  loanedQty = null;
    reservationTable.on('click', 'a.writeoff', function () {
        loanedQty = $(this).data('loaned-qty');
        if (loanedQty === 0){
            toastr.error("Nėra išduotų vadovėlių");
        }else {
            id = $(this).data('id');
            writeoffModal.find('.writeoff-quantity').text("Max nurašomų vadovėlių kiekis: " + loanedQty);
            writeoffModal.modal();
        }
    });

    $("#writeoff-submitModal").click(function (e) {
        var formData = Mvs.formToObject(this);
        var writeoffQty = $('#writeoff-quantity').val();
        var reason = $('#writeoff-reason').val();
        if(writeoffQty < 1){
            toastr.error('Nurašomas kiekis negali būti mažesnis už 1');
        }else
        if(writeoffQty > loanedQty){
            toastr.error('Nurašomas kiekis negali būti didesnis už paskolintą kieki ' + loanedQty);
        }else {
            $.ajax({
                type: "POST",
                url: '/reservation/' + id + '/writeoffQty/' + writeoffQty + '/reason/' + reason,
                data: JSON.stringify(formData),
                contentType: "application/json;charset=UTF-8",
                dataType: 'json',
                success: function () {
                    toastr.success('Vadovėlis nurašytas');
                    Dandelion.reload('#reload');
                    modal.modal('hide');
                },
                error: function () {
                    toastr.error('Nurašyti nepavyko');
                }
            });
            e.preventDefault();
        }
    });
});