$(function() {
    // Little eye
    $('body').on('mousedown', '.o_little_eye', function (ev) {
        $(ev.target).closest('.input-group').find('.form-control').prop("type",
            (i, old) => { return old === "text" ? "password" : "text"; }
        );
    });
    // db modal
    $('body').on('click', '.o_database_action', function (ev) {
        ev.preventDefault();
        var db = $(ev.currentTarget).data('db');
        var target = $(ev.currentTarget).data('target');
        $(target).find('input[name=name]').val(db);
        $(target).modal();
    });
    // close modal on submit
    $('.modal').on('submit', 'form', function (ev) {
        var form = $(this).closest('form')[0];
        if (form && form.checkValidity && !form.checkValidity()) {
            return;
        }
        var modal = $(this).parentsUntil('body', '.modal');
        if (modal.hasClass('o_database_backup')) {
            $(modal).modal('hide');
            if (!$('.alert-backup-long').length) {
                $('.list-group').before("<div class='alert alert-info alert-backup-long'>The backup may take some time before being ready</div>");
            }
        }
    });

    // generate a random master password
    // removed l1O0 to avoid confusions
    var charset = "abcdefghijkmnpqrstuvwxyz23456789";
    var password = "";
    for (var i = 0, n = charset.length; i < 12; ++i) {
        password += charset.charAt(Math.floor(Math.random() * n));
        if (i === 3 || i === 7) {
            password += "-";
        }
    }
    var master_pwds = document.getElementsByClassName("generated_master_pwd");
    for (var i=0, len=master_pwds.length|0; i<len; i=i+1|0) {
        master_pwds[i].innerText = password;
    }
    var master_pwd_inputs = document.getElementsByClassName("generated_master_pwd_input");
    for (var i=0, len=master_pwd_inputs.length|0; i<len; i=i+1|0) {
        master_pwd_inputs[i].value = password;
        master_pwd_inputs[i].setAttribute('autocomplete', 'new-password');
    }
});
