function reserve(data, type, full) {
    return Dandelion.actionButtonSpecific('Rezervuoti', 'green reserve', full.id,
        'data-quantity="' + full.quantity + '"');
}

function editBook(data, type, full) {
    return Dandelion.actionButtonSpecific('Taisyti', 'blue edit', full.id,
        'data-quantity="' + full.quantity + '"');
}

function writeoff(data, type, full) {
    return Dandelion.actionButtonSpecific('Nurayti', 'red writeoff', full.id,
        'data-quantity="' + full.quantity + '"');
}

var bookCategoriesData = [
    {id : 0, text: 'Matematika'},
    {id : 1, text: 'Lietuvių k.'},
    {id : 2, text: 'Rusų k.'},
    {id : 3, text: 'Anglų k.'},
    {id : 4, text: 'Antra Užsieno k.'},
    {id : 5, text: 'Geografija'},
    {id : 6, text: 'Biologija'},
    {id : 7, text: 'Žmogaus Sauga'},
    {id : 8, text: 'Chemija'},
    {id : 9, text: 'Istorija'},
    {id : 10, text: 'Fizika'},
    {id : 11, text: 'Dailė'},
    {id : 12, text: 'Žodynai'},
    {id : 13, text: 'Enciklopedijos'},
    {id : 14, text: 'Ekonomika'},
    {id : 15, text: 'Etika'},
    {id : 16, text: 'Gamta ir Žmogus'},
    {id : 17, text: 'Muzika'},
    {id : 18, text: 'Technologijos'},
    {id : 19, text: 'Informacinės Technologijos'},
    {id : 20, text: 'Kita'}
];

$(function () {

    Mvs.initDefaultToastr();

    var booksTable = $('#books-table');
    var modal = $('#reserve-modal');
    var editBookModal = $('#edit-book-modal')
    var writeoffModal = $('#writeoff-modal')
    var currentUser = $('#current-user').text();

    var quantity = null;
    var id = null;
    var reserveQty = null;
    var comment = null;
    booksTable.on('click', 'a.reserve', function () {
        quantity = $(this).data('quantity');
        id = $(this).data('id');

        modal.find('.quantity-label').text('Laisvų vadovėlių: ' + quantity);
        modal.modal();
    });

    modal.find('form').submit(function (e) {
        var formData = Mvs.formToObject(this);
        reserveQty = $('#reserve-qty').val();
        comment = $('#comment').val();
        if(comment === ""){
            comment = "-";
        }
        $.ajax({
            type: "POST",
            url: '/book/' + id + '/reserve/' + reserveQty + '/userId/'+currentUser+ '/comment/' + comment,
            data: JSON.stringify(formData),
            contentType: "application/json;charset=UTF-8",
            dataType: 'json',
            success: function () {
                toastr.success('Vadovėliai rezervuoti');
                Dandelion.reload('#reload');
                modal.modal('hide');
            },
            error: function () {
                toastr.error('Nėra tiek laisvų vadovėlių');
            }
        });
        e.preventDefault();
    });


    function reserveBook(id, param) {
        $.post(app.fullPath('book/' + id + '/reserve?reserve=' + param), null, function () {
            Dandelion.reload('#reload');
        });
    }

    $('#createNew').click(function () {
        $('#create-book-modal').modal();
    });

    $("#book-category").select2({
        data: bookCategoriesData
    });

    $("#edit-book-category").select2({
        data: bookCategoriesData
    });

    $("#create-submitModal").click(function (e) {
        $.ajax({
            type: "POST",
            url: '/book/create',
            data: JSON.stringify(getCreateBookData()),
            contentType: "application/json;charset=UTF-8",
            dataType: 'json',
            success: function () {
                toastr.success('Vadovėlis Sukurtas');
                Dandelion.reload('#reload');
                modal.modal('hide');
            },
            error: function () {
                toastr.error('Klaida kuriant vadovėlį');
            }
        });
        e.preventDefault();
    });

    function getCreateBookData(){
        return{
        "name": $('#book-name').val(),
        "author":  $('#book-author').val(),
        "category": $('#book-category').val(),
        "quantity": $('#book-quantity').val()
        }
    }

    booksTable.on('click', 'a.edit', function () {
        quantity = $(this).data('quantity');
        id = $(this).data('id');
        editBookModal.find('.edit-quantity').text("Laisvų vadovėlių kiekis: " + quantity);
        editBookModal.modal();
    });

    $("#edit-submitModal").click(function (e) {
        var formData = Mvs.formToObject(this);
        var editQty = $('#edit-book-quantity').val();
        $.ajax({
            type: "POST",
            url: '/book/' + id +'/editQty/' + editQty ,
            data: JSON.stringify(formData),
            contentType: "application/json;charset=UTF-8",
            dataType: 'json',
            success: function () {
                toastr.success('Vadovėlio kiekis pakeistas');
                Dandelion.reload('#reload');
                modal.modal('hide');
            },
            error: function () {
                toastr.error('Pakeisti kiekio nepavyko');
            }
        });
        e.preventDefault();
    });

    booksTable.on('click', 'a.writeoff', function () {
        quantity = $(this).data('quantity');
        id = $(this).data('id');
        writeoffModal.find('.writeoff-quantity').text("Max nurašomų vadovėlių kiekis: " + quantity);
        writeoffModal.modal();
    });

    $("#writeoff-submitModal").click(function (e) {
        var formData = Mvs.formToObject(this);
        var writeoffQty = $('#writeoff-quantity').val();
        var reason = $('#writeoff-reason').val();
        $.ajax({
            type: "POST",
            url: '/book/' + id +'/writeoffQty/' + writeoffQty + '/reason/' + reason,
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
    });
});
