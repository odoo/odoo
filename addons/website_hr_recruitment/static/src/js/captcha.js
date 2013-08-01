$(document).ready(function (event) {
    $('#defaultReal').realperson();
    $('button[type=submit]').click(function (e) {
        value = $('#defaultReal').val();
        var hash = 5381;
        for (var i = 0; i < value.length; i++) {
            hash = ((hash << 5) + hash) + value.charCodeAt(i);
        }
        $('#captchaval').val(hash);
        if ($('[name=partner_name]').val() && $('[name=email_from]').val() && $('[name=ufile]').val()){
            var flag = 0;
            if ($('#captchaval').val()) {
                var hashval = $('[name=defaultRealHash]').val();
                var captchahash = $('#captchaval').val();
                flag = 1;
            }
        }
        if (flag==1) {
            if (hashval == captchahash){
                return true;
            }else{
                $('[name=defaultReal]').focus();
                return false;
            }
        }
    });
});
