import os
from openai import OpenAI
from typing import List, Dict

# Initialize the OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize conversation history
conversation_history: List[Dict[str, str]] = []

def initialize_conversation(initial_history: List[Dict[str, str]]):
    global conversation_history
    conversation_history = initial_history[-20:]  # Keep only the last 20 messages

def get_chatbot_response(user_input: str) -> str:
    global conversation_history

    # Add user input to conversation history
    conversation_history.append({"role": "user", "content": user_input})

    # Prepare messages for the API call
    messages = [
        {"role": "system", "content": "You are a helpful assistant with a good memory. You can recall and reference previous parts of the conversation."},
    ] + conversation_history

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7
        )
        
        bot_response = response.choices[0].message.content.strip()
        
        # Add bot response to conversation history
        conversation_history.append({"role": "assistant", "content": bot_response})
        
        # Trim conversation history to last 20 messages to manage token usage
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        return bot_response
    except Exception as e:
        print(f"Error in getting chatbot response: {e}")
        return "I apologize, but I'm having trouble processing your request at the moment. Could you please try again?"

def reset_conversation():
    global conversation_history
    conversation_history = []
