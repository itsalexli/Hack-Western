import os
import json
from elevenlabs import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the ElevenLabs client with your API key
client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))

# Verify API key is set
if not os.environ.get("ELEVENLABS_API_KEY"):
    raise ValueError(
        "ELEVENLABS_API_KEY not found. Please set it in your .env file or environment variables. "
        "See Backend/README.md for setup instructions."
    )

print("🚀 ElevenLabs Conversational AI Agent Setup")
print("=" * 60)

def create_knowledge_base():
    """Create knowledge base documents from the scraped website content"""
    print("\n📚 Creating knowledge base documents...")
    
    documents = []
    
    # 1. Add the cleaned HTML content as knowledge
    try:
        with open('cleaned_output.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Extract text content from HTML for better knowledge processing
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get main text content (remove scripts, styles, etc.)
        for script in soup(["script", "style"]):
            script.decompose()
        text_content = soup.get_text(separator='\n', strip=True)
        
        # Truncate if too long (API limits)
        max_length = 100000  # Adjust based on API limits
        if len(text_content) > max_length:
            text_content = text_content[:max_length] + "\n... (content truncated)"
        
        doc_text = client.conversational_ai.knowledge_base.documents.create_from_text(
            text=text_content,
            name="Sun Life Critical Illness Insurance Page Content"
        )
        documents.append(doc_text)
        print(f"  ✓ Created text document: {doc_text.name} (ID: {doc_text.id})")
    except FileNotFoundError:
        print("  ⚠️  cleaned_output.html not found - skipping HTML content")
    except Exception as e:
        print(f"  ✗ Error creating text document: {e}")
    
    # 2. Add the original website URL as knowledge
    try:
        doc_url = client.conversational_ai.knowledge_base.documents.create_from_url(
            url="https://www.sunlife.ca/en/health/critical-illness-insurance/",
            name="Sun Life Critical Illness Insurance - Official Page"
        )
        documents.append(doc_url)
        print(f"  ✓ Created URL document: {doc_url.name} (ID: {doc_url.id})")
    except Exception as e:
        print(f"  ⚠️  Error creating URL document: {e}")
    
    return documents

def create_agent(knowledge_documents):
    """Create a new conversational AI agent"""
    print("\n🤖 Creating conversational AI agent...")
    
    # Build knowledge base configuration
    knowledge_base_config = []
    for doc in knowledge_documents:
        # Determine document type based on how it was created
        doc_type = "text" if hasattr(doc, 'text') else "url"
        knowledge_base_config.append({
            "type": doc_type,
            "name": doc.name,
            "id": doc.id
        })
    
    try:
        # Create a new agent with the knowledge base
        agent = client.conversational_ai.agents.create(
            conversation_config={
                "agent": {
                    "prompt": {
                        "prompt": """You are a helpful AI assistant for Sun Life's Critical Illness Insurance. 
Your role is to:
- Answer questions about critical illness insurance coverage and benefits
- Explain insurance terms in simple language
- Help users understand their options
- Provide information based on the Sun Life website content
- Be friendly, professional, and empathetic

Always be accurate and refer to the knowledge base when answering questions. 
If you don't know something, admit it rather than making up information.""",
                        "knowledge_base": knowledge_base_config
                    },
                    "first_message": "Hello! I'm your Sun Life assistant. I can help you understand critical illness insurance. What would you like to know?",
                    "language": "en"
                }
            }
        )
        print(f"  ✓ Agent created successfully!")
        print(f"  Agent ID: {agent.agent_id}")
        return agent
    except Exception as e:
        print(f"  ✗ Error creating agent: {e}")
        raise

def save_agent_config(agent):
    """Save agent configuration for future use"""
    config = {
        "agent_id": agent.agent_id,
        "created_at": agent.created_at if hasattr(agent, 'created_at') else None
    }
    
    with open('agent_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n💾 Agent configuration saved to agent_config.json")
    return config

def test_agent(agent_id):
    """Test the agent with a sample conversation"""
    print("\n🧪 Testing agent with sample questions...")
    print("=" * 60)
    
    try:
        # Create a conversation
        conversation = client.conversational_ai.conversations.create(agent_id=agent_id)
        print(f"Conversation ID: {conversation.conversation_id}")
        print("\n" + "=" * 60)
        
        # You can add text-based interaction here
        print("\n✅ Agent is ready to use!")
        print(f"Agent ID: {agent_id}")
        print(f"Conversation ID: {conversation.conversation_id}")
        
    except Exception as e:
        print(f"Error testing agent: {e}")

def main():
    """Main function to set up the conversational AI agent"""
    try:
        # Step 1: Create knowledge base
        documents = create_knowledge_base()
        
        if not documents:
            print("\n⚠️  No knowledge documents created. Agent will have limited knowledge.")
            print("Make sure cleaned_output.html exists in the Backend directory.")
            return
        
        # Step 2: Create agent
        agent = create_agent(documents)
        
        # Step 3: Save configuration
        config = save_agent_config(agent)
        
        # Step 4: Test agent
        test_agent(agent.agent_id)
        
        print("\n" + "=" * 60)
        print("🎉 Setup Complete!")
        print("=" * 60)
        print(f"\nYour agent is ready to use!")
        print(f"Agent ID: {agent.agent_id}")
        print(f"\nTo use this agent in your application:")
        print(f"  1. Use the agent_id from agent_config.json")
        print(f"  2. Create conversations using: client.conversational_ai.conversations.create(agent_id='{agent.agent_id}')")
        print(f"  3. Integrate with your frontend for voice interactions")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise

if __name__ == "__main__":
    main()