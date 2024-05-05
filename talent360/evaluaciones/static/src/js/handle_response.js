// Función que se ejecuta al hacer click en el botón de enviar
function handleResponseClima() {
    // Recoge todos los inputs de tipo radio
    var radios = document.querySelectorAll('.o_survey_form_choice_item');
    var selectedValues = {};
    var selectedValuesScale = {};
    radios.forEach(function(radio) {
        if (radio.checked) {
            var questionId = radio.name.split('_')[0];

            if (radio.value < 6 && radio.value > 0) {
                selectedValuesScale[questionId] = radio.value;
            } else {
                selectedValues[questionId] = radio.value;
            }
        }
    });

    // Recoge todos los elementos textarea
    var textareas = document.querySelectorAll('.o_survey_question_text_box');
    var textareaValues = {};
    textareas.forEach(function(textarea) {
        var questionId = textarea.name.split('_')[1];
        textareaValues[questionId] = textarea.value;
    });

    var evaluacion_id = document.querySelector('input[name="evaluacion_id"]').value;
    var csrf_token = document.querySelector('input[name="csrf_token"]').value;

    token = document.querySelector('input[name="token"]').value;

    // Combina los dos objetos en uno
    var data = {
        radioValues: selectedValues,
        textareaValues: textareaValues,
        evaluacion_id: evaluacion_id,
        csrf_token: csrf_token,
        token: token,
        radioValuesScale: selectedValuesScale,
    };

    console.log(data);

    // Envía los valores a la base de datos
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/evaluacion/responder', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(JSON.stringify(data));
}

// function confirmacion() {
//     // Obtén todos los campos requeridos del formulario
//     var requiredFields = document.querySelectorAll('input[required], textarea[required], select[required]');

//     // Verifica si todos los campos requeridos están llenos
//     var allFieldsFilled = Array.from(requiredFields).every(function(field) {
//         return field.value !== '';
//     });

//     if (!allFieldsFilled) {
//         alert('Por favor, llena todos los campos requeridos antes de enviar el formulario.');
//         return false;
//     }

//     if (confirm("¿Estas seguro de enviar tus respuestas?")) {
//         handleResponseClima();
//         return true;
//     } else {
//         return false;
//     }
// }