$(document).ready(function() {
    const showPasswordWrappers = document.querySelectorAll('.show__password__wrapper')
    showPasswordWrappers.forEach(showPasswordWrapper => {
        const showPasswordInput = showPasswordWrapper.querySelector('input')
        const showPasswordButton = showPasswordWrapper.querySelector('.show__password__button')
        const showPasswordIcon = showPasswordButton.querySelector('.show__password__icon')
        showPasswordButton.addEventListener('click', () => {
            const showPasswordInputType = showPasswordInput.getAttribute('type')
            if (showPasswordInputType === 'password') {
                showPasswordIcon.classList.remove('fa-eye')
                showPasswordIcon.classList.add('fa-eye-slash')
                showPasswordInput.setAttribute('type', 'text')
            } else {
                showPasswordIcon.classList.remove('fa-eye-slash')
                showPasswordIcon.classList.add('fa-eye')
                showPasswordInput.setAttribute('type', 'password')
            }
        })
    })
});
