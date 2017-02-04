function verify(data, type, full) {
    return data == true ?
        Dandelion.actionButton('Taip', 'green verify-remove', full) :
        Dandelion.actionButton('Ne', 'red verify', full);
}

function changePassword(data, type, full) {
    return Dandelion.actionButton('Pakeisti', 'red change-password', full);
}

function deleteUser(data, type, full) {
    return Dandelion.actionButton('Ištrinti', 'red delete', full);
}

$(function () {
    var usersTable = $('#users-table');

    function action(object, action) {
        var id = $(object)./*parents('tr').*/data('id');
        console.log();
        $.post(app.fullPath('account/manage/' + id + '?action=' + action), null, function () {
            location.reload();
        });
    }

    $('#createNew').click(function () {
        $('#createNewModal').modal();
    });

    $('a.change-password').click(function () {
        var id = $(this).parents('tr').data('id');
        manageModal(id);
    });

    usersTable.on('click', 'a.verify', function () {
        action(this, 'verify');
    });

    usersTable.on('click', 'a.verify-remove', function () {
        action(this, 'un-verify');
    });

    usersTable.on('click', 'a.delete', function () {
        action(this, 'delete');
    });

    usersTable.on('click','a.change-password', function () {
        var id = $(this).data('id');
        manageModal(id);
    });


    function manageModal(id){

        var modal = $('#changePasswordModal');
        var submit = $('#change-password-submit');
        modal.find('#change-password-header').text('Pakeisti Slaptažodį');
        submit.unbind();

        submit.click(function () {
            $.ajax({
                type: 'POST',
                url: '/account/manage/change-password/' + id,
                data: JSON.stringify({
                    "password" : $('#change-password').val()
                }),
                contentType: "application/json;charset=UTF-8",
                dataType: 'json',
                success: function () {
                    Dandelion.reload('#reload');
                }
            });
        });
        modal.modal();
    }


});


