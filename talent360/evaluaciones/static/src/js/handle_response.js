
function confirmacion() {
    // Obtén todos los campos requeridos del formulario
    var requiredFields = document.querySelectorAll('input[required], textarea[required], select[required], input[type="radio"][required]');
    var firstUnfilledField = null;

    // Verifica si todos los campos requeridos están llenos
    var allFieldsFilled = Array.from(requiredFields).every(function(field) {
        if (field.type === "radio") {
            // Para radio buttons, debemos verificar si alguno del grupo está seleccionado
            var radioGroup = document.getElementsByName(field.name);
            var groupChecked = Array.from(radioGroup).some(radio => radio.checked);
            if (!groupChecked && !firstUnfilledField) {
                firstUnfilledField = field;
            }
            return groupChecked;
        } else {
            var isFilled = field.value.trim() !== '';
            if (!isFilled && !firstUnfilledField) {
                firstUnfilledField = field;
            }
            return isFilled;
        }
    });

    if (!allFieldsFilled) {
        alert('Por favor, llena todos los campos requeridos antes de enviar el formulario.');
        if (firstUnfilledField) {
            firstUnfilledField.scrollIntoView({ behavior: 'smooth' });
            firstUnfilledField.focus();
        }
        return false;
    }
    return true;
}

// Función que se ejecuta al hacer click en el botón de enviar
function handleResponse(event) {

    if (event){
        event.preventDefault(); // Prevenir el comportamiento predeterminado del formulario
    }

    // Recoge todos los inputs de tipo radio
    var radios = document.querySelectorAll('.o_survey_form_choice_item');
    var selectedValues = {};
    var selectedValuesScale = {};
    radios.forEach(function(radio) {
        if (radio.checked) {
            var questionId = radio.name.split('_')[0];

            if (radio.value < 5 && radio.value >= 0) {
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
    var token = document.querySelector('input[name="token"]').value;

    // Combina los dos objetos en uno
    var data = {
        radioValues: selectedValues,
        textareaValues: textareaValues,
        evaluacion_id: evaluacion_id,
        csrf_token: csrf_token,
        token: token,
        radioValuesScale: selectedValuesScale,
    };

    var conf = confirmacion();
    
    if (conf) {
        if (confirm("¿Estás seguro de enviar tus respuestas?")) {
            // Envía los valores a la base de datos
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/evaluacion/responder', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.send(JSON.stringify(data));

            // Muestra un mensaje de confirmación
            alert('¡Sus respuestas han sido enviadas!');
            location.reload();
        }
    }
}

// Asegúrate de agregar el evento preventDefault en el envío del formulario
document.querySelector('form').addEventListener('submit', handleResponse);

function iniciar_evaluacion() {
    boton_responder = document.querySelector("#boton_responder");
    contenedor_preguntas = document.querySelector("#contenedor_preguntas");

    boton_responder.style.display = "none";
    contenedor_preguntas.style.display = "block";
}