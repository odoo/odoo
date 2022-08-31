$(function () {
    // Little eye
    $("body").on("mousedown", ".o_little_eye", function (ev) {
        $(ev.target)
            .closest(".input-group")
            .find(".form-control")
            .prop("type", (i, old) => {
                return old === "text" ? "password" : "text";
            });
    });
    // db modal
    $("body").on("click", ".o_database_action", function (ev) {
        ev.preventDefault();
        const db = $(ev.currentTarget).data("db");
        const target = $(ev.currentTarget).data("bsTarget");
        $(target).find("input[name=name]").val(db);
        $(target).modal("show");
    });
    // close modal on submit
    $(".modal").on("submit", "form", function (ev) {
        const form = $(this).closest("form")[0];
        if (form && form.checkValidity && !form.checkValidity()) {
            return;
        }
        const modal = $(this).parentsUntil("body", ".modal");
        if (modal.hasClass("o_database_backup")) {
            $(modal).modal("hide");
            if (!$(".alert-backup-long").length) {
                $(".list-group").before(
                    "<div class='alert alert-info alert-backup-long'>The backup may take some time before being ready</div>"
                );
            }
        }
    });

    // generate a random master password
    // removed l1O0 to avoid confusions
    const charset = "abcdefghijkmnpqrstuvwxyz23456789";
    let password = "";
    for (let i = 0, n = charset.length; i < 12; ++i) {
        password += charset.charAt(Math.floor(Math.random() * n));
        if (i === 3 || i === 7) {
            password += "-";
        }
    }
    const master_pwds = document.getElementsByClassName("generated_master_pwd");
    for (let i = 0, len = master_pwds.length | 0; i < len; i = (i + 1) | 0) {
        master_pwds[i].innerText = password;
    }
    const master_pwd_inputs = document.getElementsByClassName("generated_master_pwd_input");
    for (let i = 0, len = master_pwd_inputs.length | 0; i < len; i = (i + 1) | 0) {
        master_pwd_inputs[i].value = password;
        master_pwd_inputs[i].setAttribute("autocomplete", "new-password");
    }
});
