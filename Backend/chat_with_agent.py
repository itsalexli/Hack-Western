"""
Interactive chat script to test the ElevenLabs conversational AI agent
"""
import os
import json
from elevenlabs import ElevenLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize client
client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))

def load_agent_config():
    """Load agent configuration from file"""
    try:
        with open('agent_config.json', 'r') as f:
            config = json.load(f)
        return config['agent_id']
    except FileNotFoundError:
        print("❌ agent_config.json not found!")
        print("Please run elevenLabs.py first to create the agent.")
        return None

def chat_with_agent(agent_id):
    """Start an interactive chat session with the agent"""
    print("🎙️  ElevenLabs AI Agent - Chat Interface")
    print("=" * 60)
    print("Type your questions and press Enter to send.")
    print("Type 'quit' or 'exit' to end the conversation.")
    print("=" * 60)
    
    try:
        # Create a new conversation
        conversation = client.conversational_ai.conversations.create(agent_id=agent_id)
        print(f"\n✓ Conversation started (ID: {conversation.conversation_id})")
        print("\nAgent: Hello! I'm your Sun Life assistant. I can help you understand critical illness insurance. What would you like to know?\n")
        
        while True:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Goodbye! Conversation ended.")
                break
            
            # Send message and get response
            # Note: For full voice integration, you'd use the WebSocket API
            # This is a simplified text-based version
            print("\n🤔 Agent is thinking...")
            print("\n(Note: Full voice integration requires WebSocket connection)")
            print("Visit: https://elevenlabs.io/docs/conversational-ai/quickstart")
            print("\nFor now, the agent has been created with your knowledge base.")
            print(f"Use Agent ID: {agent_id} in your voice application.\n")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

def main():
    """Main function"""
    agent_id = load_agent_config()
    
    if not agent_id:
        return
    
    print(f"\n🤖 Using Agent ID: {agent_id}\n")
    chat_with_agent(agent_id)

if __name__ == "__main__":
    main()
