// chat.js
function startChat() {
    console.log('Start Chat clicked');
    var selectedKey = $("input[name='selected_document_text_key']:checked").val();
    if (selectedKey) {
        // Show the chat form
        $('#chatForm').show();
        $('#chatStartForm').hide();
    }
}

function submitInquiry() {
    var userQuery = $('#user_query').val();
    var selectedKey = $("input[name='selected_document_text_key']:checked").val();

    // Send the question to the server
    $.ajax({
        url: '/chat_document',
        type: 'POST',
        data: { selected_document_text_key: selectedKey, user_query: userQuery },
        dataType: 'json',
        success: function(data) {
            console.log('Server response:', data);

            // Update the chat interface
            var chatContent = $('#chatContent');

            var userMessage = $('<div>').addClass('message user-message')
                .append($('<span>').addClass('user-name').text('You:'))
                .append(' ' + userQuery);

            // Access the 'result' property from the response object
            var aiMessage = $('<div>').addClass('message ai-message')
                .append($('<span>').addClass('user-name').text('AI:'))
                .append(' ' + data.answer.result);

            chatContent.append(userMessage);
            chatContent.append(aiMessage);

            // Clear the input field
            $('#user_query').val('');
        },
        error: function(error) {
            console.log('Error:', error);
        }
    });
}


function showForm() {
    document.getElementById('formContainer').style.display = 'block';
}