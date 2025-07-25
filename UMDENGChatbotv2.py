# Implementation of PII patterns to redact certain info, add a chat history, and limited interests tracker
import gradio as gr
import json
import requests
import re
from typing import List, Dict, Any
import csv
import os
from datetime import datetime

# --- 👇 Add PII detection patterns ---
PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b(?:\+?1[-.\s]?|0)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
    "zip": r"\b\d{5}(?:-\d{4})?\b"
}

def detect_pii(text: str) -> list:
    found = []
    for label, pattern in PII_PATTERNS.items():
        if re.search(pattern, text):
            found.append(label)
    return found

def remove_pii(text: str) -> str:
    for pattern in PII_PATTERNS.values():
        text = re.sub(pattern, "[REDACTED]", text)
    return text

# --- 👇 Add user profile tracker ---
user_profile = {
    "interests": [],
    "goals": []
}

# Your API key (Note: Keep this secure in production!)
API_KEY = "6K3XE9j39N7LUjHYmGHSJbYFaQR6UWBk"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


# Load the UMD program data
UMD_PROGRAMS_DATA = [
 {
   "url": "https://www.nanocenter.umd.edu/education/nano-minor/",
   "title": "Nano Minor | Maryland NanoCenter",
   "program_name": "Nanoscience and Technology",
   "program_type": "Minor",
   "primary_keywords": ["nanotechnology", "materials", "microscale", "research"],
   "secondary_keywords": ["fabrication", "characterization", "quantum effects", "surfaces"],
   "career_focus": ["research scientist", "nanotechnology engineer"],
   "technology_areas": ["nanofabrication", "material characterization", "device development"],
   "industry_applications": ["electronics", "materials", "pharmaceutical", "research"],
   "content": "The Maryland nano community has increasingly focused its educational offerings at both the undergraduate and graduate level on nanoscale science and engineering targets of its various traditional disciplines, leading to an evolution of focus, example, and projects in existing courses as well as the generation of new courses. To meet the rapidly growing interest of students in nano, and to create the nano workforce of the future, Maryland NanoCenter is in the process of finalizing an innovative undergraduate program, the Interdisciplinary Minor Program in Nanoscale Science and Technology.",
   "specializations": "Nanomaterials, Nanobiotechnology, Nanoelectronics, or Nanoengineering"
 },
 {
   "url": "https://me.umd.edu/undergraduate/degrees/minor-nuclear-engineering",
   "title": "Minor in Nuclear Engineering | Department of Mechanical Engineering",
   "program_name": "Nuclear Engineering",
   "program_type": "Minor",
   "primary_keywords": ["nuclear", "radiation", "energy", "power"],
   "secondary_keywords": ["reactors", "safety", "waste management", "physics"],
   "career_focus": ["nuclear engineer", "radiation safety officer", "power engineer"],
   "technology_areas": ["reactor design", "radiation protection", "nuclear fuel"],
   "industry_applications": ["nuclear power", "national labs", "medical applications"],
   "content": "Nuclear power currently accounts for approximately 20% of electricity generation in the United States. With 104 operating reactors, the U.S. has more installed nuclear capacity than any nation in the world. The minor in Nuclear Engineering provides the engineering student with the understanding of nuclear engineering and its application to many different fields, such as power generation, reactor operation, and industrial uses.",
   "specializations": "Nuclear Reactor Design, Power Systems"
 },
 {
   "url": "https://pm.umd.edu/program/undergraduate-minor-in-project-management/",
   "title": "Undergraduate Minor in Project Management | University of Maryland Project Management",
   "program_name": "Project Management",
   "program_type": "Minor",
   "primary_keywords": ["management", "planning", "organization", "leadership"],
   "secondary_keywords": ["scheduling", "budgeting", "risk management", "teams"],
   "career_focus": ["project manager", "program manager", "team leader"],
   "technology_areas": ["project planning", "resource management", "risk assessment"],
   "industry_applications": ["all engineering industries", "consulting", "technology"],
   "content": "The UMD Project Management Minor prepares undergraduates to launch their careers by equipping them with comprehensive project management knowledge, tools, and techniques, enabling them to excel on project teams and advance into leadership roles.",
   "specializations": "Project Planning and Scheduling, Risk Management, Team Leadership and Collaboration"
 },
 {
   "url": "https://ece.umd.edu/undergraduate/degrees/minor-quantum-science-and-engineering",
   "title": "Minor in Quantum Science and Engineering | Department of Electrical and Computer Engineering",
   "program_name": "Quantum Science and Engineering",
   "program_type": "Minor",
   "primary_keywords": ["quantum", "physics", "computing", "advanced technology"],
   "secondary_keywords": ["quantum mechanics", "information theory", "materials", "science", "technology"],
   "career_focus": ["quantum engineer", "research scientist", "technology developer"],
   "technology_areas": ["quantum computing", "quantum communications", "quantum sensing"],
   "industry_applications": ["tech companies", "research institutions", "defense"],
   "content": "The program draws upon courses from multiple departments including Electrical Engineering, Physics, Computer Science, and Materials Science to provide students with a comprehensive understanding of quantum phenomena and their technological applications.",
   "specializations": "Quantum computing technologies, Quantum materials, Quantum hardware, Quantum computers"
 },
 {
   "url": "https://robotics.umd.edu/minor",
   "title": "Robotics and Autonomous Systems (RAS) Minor | Maryland Robotics Center",
   "program_name": "Robotics and Autonomous Systems",
   "program_type": "Minor",
   "primary_keywords": ["robotics", "automation", "AI", "autonomous"],
   "secondary_keywords": ["sensors", "control systems", "machine learning", "programming", "design"],
   "career_focus": ["robotics engineer", "AI engineer", "automation specialist"],
   "technology_areas": ["robot design", "autonomous navigation", "AI algorithms"],
   "industry_applications": ["manufacturing", "healthcare", "defense", "transportation"],
   "content": "The undergraduate minor in Robotics and Autonomous Systems (RAS) is a cross-disciplinary 2 year long program administered by the Maryland Robotics Center in the Institute for Systems Research within the A. James Clark School of Engineering.",
   "specializations": "design, control, programming"
 },
 {
   "url": "https://ece.umd.edu/undergraduate/degrees/minor-computer-engineering",
   "title": "Minor in Computer Engineering | Department of Electrical and Computer Engineering", 
   "program_name": "Computer Engineering",
   "program_type": "Minor",
   "primary_keywords": ["computers", "programming", "digital systems", "hardware"],
   "secondary_keywords": ["embedded systems", "microprocessors", "software development"],
   "career_focus": ["supplement to other engineering disciplines"],
   "technology_areas": ["digital design", "programming", "computer architecture"],
   "industry_applications": ["enhances primary engineering field with computing"],
   "content": "The undergraduate Minor in Computer Engineering introduces students to core hardware concepts such as computer architecture, digital logic design, and digital circuit design—as well as core software concepts—such as algorithms, discrete mathematics, and programming.",
   "specializations": "Foundations of Machine Learning, Microprocessors, Digital Computer Design, Cryptography, Computer Security, Digital CMOS VLSI, Parallel Algorithms, Embedded Systems"
 },
 {
   "url": "https://pm.umd.edu/program/cpm-minor/",
   "title": "Undergraduate Minor in Construction Project Management | University of Maryland Project Management",
   "program_name": "Construction Project Management",
   "program_type": "Minor",
   "primary_keywords": ["construction", "management", "projects", "planning"],
   "secondary_keywords": ["scheduling", "budgeting", "contracts", "coordination"],
   "career_focus": ["project manager", "construction manager", "site supervisor"],
   "technology_areas": ["project planning", "cost control", "team management"],
   "industry_applications": ["construction", "real estate development", "infrastructure"],
   "content": "Undergraduate students wishing to pursue a career in the design or construction of capital projects will have a distinct competitive advantage if they have a working knowledge of the fundamentals of managing construction.",
   "specializations": ""
 },
 {
   "url": "https://eng.umd.edu/global/coursework",
   "title": "Minor in Global Engineering Leadership | A. James Clark School of Engineering, University of Maryland",
   "program_name": "Global Engineering Leadership",
   "program_type": "Minor",
   "primary_keywords": ["leadership", "international", "management", "global"],
   "secondary_keywords": ["cultural competency", "project management", "communication"],
   "career_focus": ["engineering manager", "international project leader"],
   "technology_areas": ["cross-cultural communication", "global project management"],
   "industry_applications": ["multinational companies", "international development"],
   "content": "The minor in global engineering leadership is designed to develop the skills necessary to lead with a global vision, work effectively with others to address social issues, and engineer solutions that improve communities and organizations.",
   "specializations": "Global perspectives focus (e.g. international development, sustainability, global health), Leadership focus (e.g. project management, entrepreneurship, strategic planning)"
 },
 {
   "url": "https://chbe.umd.edu/undergraduate/degrees/bachelor-science",
   "title": "Bachelor of Science | Department of Chemical and Biomolecular Engineering",
   "program_name": "Chemical Engineering",
   "program_type": "Major",
   "primary_keywords": ["chemistry", "processes", "manufacturing", "materials"],
   "secondary_keywords": ["reactions", "separation", "thermodynamics", "kinetics"],
   "career_focus": ["process engineer", "plant engineer", "research engineer"],
   "technology_areas": ["process design", "reactor engineering", "separation processes"],
   "industry_applications": ["chemical plants", "oil & gas", "food processing"],
   "content": "The educational mission of the Department of Chemical and Biomolecular Engineering is to provide students with a fundamental understanding of physical, chemical and biological processes and with the ability to apply molecular and biomolecular information and methods of discovery into products and the processes by which they are made.",
   "specializations": []
 },
 {
   "url": "https://cee.umd.edu/undergraduate/degrees/bachelor-science",
   "title": "Bachelor of Science | Department of Civil & Environmental Engineering",
   "program_name": "Civil Engineering",
   "program_type": "Major",
   "primary_keywords": ["construction", "infrastructure", "buildings", "transportation"],
   "secondary_keywords": ["structures", "geotechnical", "water resources", "environmental"],
   "career_focus": ["structural engineer", "transportation engineer", "project manager"],
   "technology_areas": ["concrete design", "bridge engineering", "traffic systems"],
   "industry_applications": ["construction companies", "government agencies", "consulting"],
   "content": "The department provides an educational program of basic and specialized engineering knowledge necessary for its graduates to be proficient in recognized specialties. In addition to general and technical education, the educational program stresses professional and ethical responsibilities, an awareness of societal issues, and the need for life-long learning.",
   "specializations": []
 },
 {
   "url": "https://ece.umd.edu/undergraduate/degrees/bs-computer-engineering",
   "title": "B.S. in Computer Engineering | Department of Electrical and Computer Engineering",
   "program_name": "Computer Engineering",
   "program_type": "Major",
   "primary_keywords": ["computers", "hardware", "software", "programming"],
   "secondary_keywords": ["microprocessors", "embedded systems", "digital design", "circuits"],
   "career_focus": ["software engineer", "hardware engineer", "systems engineer"],
   "technology_areas": ["processor design", "embedded programming", "digital systems"],
   "industry_applications": ["tech companies", "semiconductor", "telecommunications"],
   "content": "Computer engineers apply the principles and techniques of electrical engineering, computer science, and mathematical analysis to the design, development, testing, and evaluation of the software and hardware systems that enable computers to perform increasingly demanding functions.",
   "specializations": []
 },
 {
   "url": "https://mse.umd.edu/undergraduate/degrees/bachelor-science",
   "title": "Bachelor of Science | Department of Materials Science and Engineering",
   "program_name": "Materials Science and Engineering",
   "program_type": "Major",
   "primary_keywords": ["materials", "metals", "polymers", "ceramics", "biomaterials", "AMASE"],
   "secondary_keywords": ["nanotechnology", "composites", "characterization", "properties", "structure", "surfaces", "semiconductors", "processing"],
   "career_focus": ["materials engineer", "research scientist", "quality engineer"],
   "technology_areas": ["material development", "testing", "characterization"],
   "industry_applications": ["aerospace", "automotive", "electronics", "research"],
   "content": "Materials Science and Engineering is a multidisciplinary field focused on developing materials, devices and systems that provide the foundation for advancing technology.",
   "specializations": ["Materials Science", "Soft Materials and Biomaterials", "Materials for Applications", "Materials for Energy"]
 },
 {
   "url": "https://me.umd.edu/academics/degrees/bs-in-mechanical-engineering",
   "title": "B.S. in Mechanical Engineering | Department of Mechanical Engineering",
   "program_name": "Mechanical Engineering",
   "program_type": "Major",
   "primary_keywords": ["mechanics", "machines", "design", "manufacturing", "product engineering"],
   "secondary_keywords": ["thermodynamics", "fluid mechanics", "dynamics", "CAD", "automotive", "CFD", "FEA", "process development"],
   "career_focus": ["mechanical engineer", "design engineer", "manufacturing engineer"],
   "technology_areas": ["machine design", "HVAC", "manufacturing processes"],
   "industry_applications": ["automotive", "aerospace", "manufacturing", "energy"],
   "content": "From design to manufacturing, we bring innovative ideas to the laboratory and the world. Students in Mechanical Engineering choose between one of six concentration areas to tailor their interests and learning experiences.",
   "specializations": ["Aero/Mechanical Industry", "Automotive Design", "Design and Manufacturing", "Energy and the Environment", "Engineering Management", "Robotics and Mechatronics"]
 },
 {
   "url": "https://shadygrove.umd.edu/academics/degree-programs/bs-mechatronics-engineering",
   "title": "B.S. in Mechatronics Engineering | The Universities at Shady Grove",
   "program_name": "Mechatronics Engineering",
   "program_type": "Major",
   "primary_keywords": ["robotics", "automation", "mechanical", "electrical", "electronics"],
   "secondary_keywords": ["sensors", "actuators", "control systems", "programming"],
   "career_focus": ["mechatronics engineer", "automation engineer", "robotics engineer"],
   "technology_areas": ["robotic systems", "automated manufacturing", "control"],
   "industry_applications": ["manufacturing", "robotics companies", "automotive"],
   "content": "Mechatronics is the combination of mechanical, electrical, and information systems engineering. Mechatronics engineers design, develop, and test automated production systems, transportation and vehicle systems, robotics, computer-machine controls, and many other integrated systems.",
   "specializations": []
 },
 {
   "url": "https://aero.umd.edu/undergraduate/degrees/bachelor-science",
   "title": "Bachelor of Science | Department of Aerospace Engineering",
   "program_name": "Aerospace Engineering",
   "program_type": "Major",
   "primary_keywords": ["aerospace", "aviation", "flight", "space", "aeronautics", "astronautics"],
   "secondary_keywords": ["rockets", "satellites", "aircraft", "propulsion", "wind tunnel", "navigation", "neutral buoyancy", "missiles", "helicopters", "supersonic", "hypersonic"],
   "career_focus": ["astronautical engineer", "aeronautical engineer", "flight systems engineer"],
   "technology_areas": ["propulsion systems", "avionics", "spacecraft design"],
   "industry_applications": ["NASA", "Boeing", "Lockheed Martin", "SpaceX"],
   "content": "The Department of Aerospace Engineering features state-of-the-art laboratories such as hypersonic wind tunnels and a neutral bouyancy facility. Students in Aerospace Engineering can choose between five subdisciplines to tailor their interests and learning experiences.",
   "specializations": ["aerodynamics", "flight dynamics and control", "propulsion", "materials and structures", "systems design", "space", "air"]
 },
 {
   "url": "https://biocomp.umd.edu/",
   "title": "Overview | B.S. in Biocomputational Engineering",
   "program_name": "Biocomputational Engineering",
   "program_type": "Major",
   "primary_keywords": ["biology", "computation", "data analysis", "bioinformatics", "biotech", "medicine"],
   "secondary_keywords": ["modeling", "simulation", "genomics", "proteomics", "molecular", "life science", "pharmaceutical"],
   "career_focus": ["computational biologist", "bioinformatics engineer", "data scientist", "geneticist"],
   "technology_areas": ["machine learning", "genomic analysis", "biological modeling", "molecular lab", "data visualization"],
   "industry_applications": ["pharmaceutical", "biotechnology", "research institutes", "NIH"],
   "content": "The new bachelor of science in biocomputational engineering degree program will address the rapidly growing demand for engineers with expertise in both the biological sciences and computational methods.",
   "specializations": []
 },
 {
   "url": "https://bioe.umd.edu/undergraduate/bachelor-science",
   "title": "B.S. in Bioengineering | Fischell Department of Bioengineering",
   "program_name": "Bioengineering",
   "program_type": "Major",
   "primary_keywords": ["biology", "medical", "healthcare", "biomedicine", "BIOE"],
   "secondary_keywords": ["tissue engineering", "medical devices", "biomaterials", "genetics", "BioWorkshop", "rehabilitation", "cell"],
   "career_focus": ["biomedical engineer", "medical device engineer", "research scientist"],
   "technology_areas": ["prosthetics", "medical imaging", "drug delivery"],
   "industry_applications": ["medical device companies", "hospitals", "pharmaceutical"],
   "content": "The Bioengineering curriculum is designed to emphasize strong fundamentals in both engineering and biology, to include experiential learning in the engineering practices, and to align with specific careers in bioengineering sub-fields.",
   "specializations": []
 },
 {
   "url": "https://spp.umd.edu/science-technology-ethics-and-policy-step-minor",
   "title": "Science, Technology, Ethics and Policy (STEP) Minor | UMD School of Public Policy",
   "program_name": "Science Technology Ethics and Policy",
   "program_type": "Minor",
   "primary_keywords": ["ethics", "policy", "society", "technology impact"],
   "secondary_keywords": ["regulation", "environmental impact", "social responsibility"],
   "career_focus": ["policy analyst", "technology consultant", "ethics officer"],
   "technology_areas": ["technology assessment", "policy development", "ethical analysis"],
   "industry_applications": ["government", "consulting", "non-profits", "tech companies"],
   "content": "The STEP minor is an interdisciplinary program that offers you the knowledge and analytical skills to understand and assess the complex interactions among science, technology, and society.",
   "specializations": ["Social, Ethical & Policy Implications", "Science & Technology Development", "Information Economy", "Sustainability, Social Responsibility & Engineering"]
 },
 {
   "url": "http://www.mtech.umd.edu/educate/minor/",
   "title": "Technology Entrepreneurship Minor",
   "program_name": "Technology Entrepreneurship",
   "program_type": "Minor",
   "primary_keywords": ["business", "startups", "innovation", "commercialization"],
   "secondary_keywords": ["venture capital", "intellectual property", "marketing"],
   "career_focus": ["entrepreneur", "technology manager", "business developer"],
   "technology_areas": ["business development", "product commercialization", "innovation"],
   "industry_applications": ["startups", "venture capital", "technology transfer"],
   "content": "The Technology Entrepreneurship minor provides students with the knowledge and skills needed to identify, evaluate, and develop technology-based business opportunities.",
   "specializations": "None"
 },
 {
   "url": "https://shadygrove.ece.umd.edu/",
   "title": "Overview | Cyber-Physical Systems Engineering",
   "program_name": "Cyber-Physical Systems Engineering",
   "program_type": "Major",
   "primary_keywords": ["cybersecurity", "physical systems", "IoT", "automation"],
   "secondary_keywords": ["sensors", "networks", "control systems", "security"],
   "career_focus": ["systems engineer", "cybersecurity engineer", "automation engineer"],
   "technology_areas": ["industrial control", "smart systems", "network security"],
   "industry_applications": ["manufacturing", "utilities", "defense", "smart cities"],
   "content": "The Bachelor of Science in Cyber-Physical Systems Engineering (CPSE) provides students with a solid foundation in key emerging technologies of the Internet of Things (loT), the ability to integrate devices into complete loT systems.",
   "specializations": ["Networks", "Cybersecurity", "Machine Learning"]
 },
 {
   "url": "https://ece.umd.edu/undergraduate/degrees/bs-electrical-engineering",
   "title": "B.S. in Electrical Engineering | Department of Electrical and Computer Engineering",
   "program_name": "Electrical Engineering",
   "program_type": "Major",
   "primary_keywords": ["electricity", "electronics", "power", "circuits"],
   "secondary_keywords": ["signal processing", "communications", "control systems", "power"],
   "career_focus": ["electrical engineer", "power engineer", "electronics engineer"],
   "technology_areas": ["power generation", "telecommunications", "control systems"],
   "industry_applications": ["utilities", "electronics companies", "telecommunications"],
   "content": "Electrical engineers create innovative technology solutions in a wide range of areas from handheld communications to solar panels; from cardiac pacemakers to autonomous robots; from wireless networks to bio-engineered sensors that detect dangerous pathogens.",
   "specializations": ["Power Systems", "Communications", "Microelectronics"]
 },
 {
   "url": "https://fpe.umd.edu/undergraduate/degrees/bachelor-science",
   "title": "Bachelor of Science (On-Campus & Online) | Department of Fire Protection Engineering",
   "program_name": "Fire Protection Engineering",
   "program_type": "Major",
   "primary_keywords": ["fire safety", "building codes", "safety systems", "prevention"],
   "secondary_keywords": ["sprinkler systems", "smoke detection", "emergency egress", "codes"],
   "career_focus": ["fire protection engineer", "safety engineer", "code consultant"],
   "technology_areas": ["fire suppression", "safety analysis", "building design"],
   "industry_applications": ["consulting firms", "insurance", "government agencies"],
   "content": "Fire Protection Engineers protect people, property, and the environment from the unwanted effects of fire. Our undergraduate degree program provides a fundamental engineering education alongside unique interdisciplinary coursework.",
   "specializations": ["Fire Modeling", "Risk Assessment", "Building Design"]
 }
]


def search_programs(user_interests: str) -> List[Dict[str, Any]]:
   """
   Search through UMD programs based on user interests
   Returns a list of matching programs with relevance scores
   """
   user_interests_lower = user_interests.lower()
   matches = []
  
   for program in UMD_PROGRAMS_DATA:
       score = 0
       matched_keywords = []
      
       # Check primary keywords (higher weight)
       for keyword in program.get("primary_keywords", []):
           if keyword.lower() in user_interests_lower:
               score += 3
               matched_keywords.append(keyword)
      
       # Check secondary keywords
       for keyword in program.get("secondary_keywords", []):
           if keyword.lower() in user_interests_lower:
               score += 2
               matched_keywords.append(keyword)
      
       # Check career focus
       for career in program.get("career_focus", []):
           if any(word in user_interests_lower for word in career.lower().split()):
               score += 2
               matched_keywords.append(career)
      
       # Check industry applications
       for industry in program.get("industry_applications", []):
           if industry.lower() in user_interests_lower:
               score += 1
               matched_keywords.append(industry)
      
       # Check program name
       program_words = program["program_name"].lower().split()
       for word in program_words:
           if word in user_interests_lower:
               score += 2
               matched_keywords.append(word)
      
       if score > 0:
           matches.append({
               "program": program,
               "score": score,
               "matched_keywords": matched_keywords
           })
  
   # Sort by score (highest first) and return top matches
   matches.sort(key=lambda x: x["score"], reverse=True)
   return matches[:5]  # Return top 5 matches


def call_mistral_api(messages: List[Dict[str, str]]) -> str:
   """
   Call the Mistral API with conversation messages
   """
   headers = {
       "Authorization": f"Bearer {API_KEY}",
       "Content-Type": "application/json"
   }
  
   data = {
       "model": "mistral-medium",
       "messages": messages,
       "max_tokens": 1000,
       "temperature": 0.7
   }
  
   try:
       response = requests.post(MISTRAL_API_URL, headers=headers, json=data)
       response.raise_for_status()
      
       result = response.json()
       return result["choices"][0]["message"]["content"]
      
   except requests.exceptions.RequestException as e:
       return f"Sorry, I'm having trouble connecting to my AI service. Please try again later. Error: {str(e)}"
   except KeyError as e:
       return f"Sorry, I received an unexpected response. Please try again. Error: {str(e)}"


def create_program_summary(program_data: Dict[str, Any]) -> str:
   """
   Create a formatted summary of a program
   """
   program = program_data["program"]
  
   summary = f"**{program['program_name']} ({program['program_type']})**\n\n"
   summary += f"📋 **Overview:** {program['content'][:200]}...\n\n"
  
   if program.get('career_focus'):
       summary += f"💼 **Career Opportunities:** {', '.join(program['career_focus'])}\n\n"
  
   if program.get('industry_applications'):
       summary += f"🏭 **Industries:** {', '.join(program['industry_applications'])}\n\n"
  
   if program.get('specializations') and program['specializations']:
       summary += f"🎯 **Specializations:** {program['specializations']}\n\n"
  
   summary += f"🔗 **More Info:** {program['url']}\n"
   summary += "---\n"
  
   return summary


def chatbot_response(message: str, history: List[List[str]]) -> str:
   """
   Main chatbot function that processes user input and returns response
   """
   if not message.strip():
       return "Please tell me about your interests so I can help you find the right UMD engineering program!"
  
   # Search for relevant programs
   matching_programs = search_programs(message)
  
   # Create context for the AI
   context = "You are a helpful academic advisor for the University of Maryland A. James Clark School of Engineering. "
   context += "Help students choose between engineering majors and minors based on their interests. "
   context += "Be encouraging, informative, and personalized in your responses. "
  
   if matching_programs:
       context += "Here are the most relevant UMD engineering programs based on the student's interests:\n\n"
       for i, match in enumerate(matching_programs[:3], 1):
           program = match["program"]
           context += f"{i}. {program['program_name']} ({program['program_type']})\n"
           context += f"   - Description: {program['content'][:150]}...\n"
           context += f"   - Career paths: {', '.join(program.get('career_focus', []))}\n"
           context += f"   - Industries: {', '.join(program.get('industry_applications', []))}\n\n"
  
   # Prepare messages for the API
   messages = [
       {"role": "system", "content": context},
       {"role": "user", "content": message}
   ]
  
   # Add conversation history (last 4 exchanges to keep context manageable)
   if history:
       for exchange in history[-4:]:
           if len(exchange) >= 2:
               messages.insert(-1, {"role": "user", "content": exchange[0]})
               messages.insert(-1, {"role": "assistant", "content": exchange[1]})
  
   # Get AI response
   ai_response = call_mistral_api(messages)
  
   # Add program details if matches were found
   if matching_programs:
       ai_response += "\n\n## 📚 Detailed Program Information:\n\n"
       for match in matching_programs[:3]:
           ai_response += create_program_summary(match)
  
   return ai_response

def handle_message_submission(message, history):
    if message.strip():
        # Step 1: PII Detection
        pii_found = detect_pii(message)
        if pii_found:
            alert = f"⚠️ Privacy Alert: We detected possible sensitive information in your message ({', '.join(pii_found)}). It has been removed for your safety."
            message = remove_pii(message)
            response = alert + "\n\nPlease rephrase your message without personal details.\n"
        else:
            # Step 2: Track relevant keywords as interests
            keywords = message.lower().split()
            for word in keywords:
                if word in ['robotics', 'ai', 'materials', 'space', 'bioengineering', 'energy', 'programming']:
                    if word not in user_profile["interests"]:
                        user_profile["interests"].append(word)

            # Step 3: Generate response
            response = chatbot_response(message, history)

        # Step 4: Update interests display
        interests_text = f"<div style='color:#888; font-size:14px; padding-top:10px;'>🔎 <strong>Tracked Interests:</strong> {', '.join(user_profile['interests']) if user_profile['interests'] else 'None yet'}</div>"
        
        # Step 5: Return updated chat history
        updated_history = history + [(message, response)]
        return updated_history, "", interests_text
    
    return history, "", f"<div style='color:#888; font-size:14px; padding-top:10px;'>🔎 <strong>Tracked Interests:</strong> {', '.join(user_profile['interests']) if user_profile['interests'] else 'None yet'}</div>"


def get_chat_history(history):
    return "\n\n".join([f"👤 {user}\n🤖 {bot}" for user, bot in history])

def save_history_to_file(history):
    with open("chat_history.txt", "w") as f:
        for user, bot in history:
            f.write(f"User: {user}\nBot: {bot}\n\n")
    return "✅ Chat history saved to chat_history.txt"

def create_interface():
    """
    Create and configure the Gradio interface
    """
    css = """
    .gradio-container {
        max-width: 800px !important;
        margin: auto !important;
    }
    .chat-message {
        padding: 10px !important;
        margin: 5px 0 !important;
    }
    .title {
        text-align: center;
        color: #d73027;
        font-weight: bold;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-style: italic;
    }
    """

    with gr.Blocks(css=css, title="UMD Engineering Advisor") as interface:
        gr.HTML("""
            <div style="text-align: center; padding: 20px;">
                <h1 style="color: #d73027; margin-bottom: 10px;">🎓 UMD Engineering Academic Advisor</h1>
                <h3 style="color: #666; font-weight: normal;">A. James Clark School of Engineering</h3>
                <p style="color: #888; font-size: 16px;">
                    Get personalized recommendations for engineering majors and minors based on your interests!
                </p>
            </div>
        """)

        # Add this as a component that can be updated
        interests_display = gr.HTML(value="<div style='color:#888; font-size:14px; padding-top:10px;'>🔎 <strong>Tracked Interests:</strong> None yet</div>")

        chatbot = gr.Chatbot(
            height=500,
            show_label=False,
            avatar_images=["🧑‍🎓", "🤖"],
            bubble_full_width=False
        )

        with gr.Row():
            msg = gr.Textbox(
                placeholder="Tell me about your interests! (e.g., 'I like building robots and programming' or 'I'm interested in sustainable energy')",
                show_label=False,
                container=False,
                scale=4
            )
            submit_btn = gr.Button("Send", variant="primary", scale=1)

        with gr.Row():
            clear_btn = gr.Button("Clear Chat", variant="secondary")

        # 🧠 Add chat history output
        history_output = gr.Textbox(label="Full Chat History", lines=10, interactive=False)

        with gr.Row():
            view_btn = gr.Button("🔍 View Chat History")
            save_btn = gr.Button("💾 Save Chat to File")

        # 💬 Click actions
        submit_btn.click(handle_message_submission, inputs=[msg, chatbot], outputs=[chatbot, msg, interests_display])
        msg.submit(handle_message_submission, inputs=[msg, chatbot], outputs=[chatbot, msg, interests_display])
        clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg])
        view_btn.click(get_chat_history, inputs=[chatbot], outputs=[history_output])
        save_btn.click(save_history_to_file, inputs=[chatbot], outputs=[history_output])

        # ✅ Fixed HTML (no Python code inside!)
        gr.HTML("""
            <div style="text-align: center; padding: 20px; color: #888; font-size: 14px;">
                <p>💡 <strong>Tips for better recommendations:</strong></p>
                <ul style="text-align: left; display: inline-block;">
                    <li>Mention specific technologies, fields, or activities you enjoy</li>
                    <li>Tell me about your career goals or dream job</li>
                    <li>Ask about specific programs or compare different options</li>
                    <li>Mention if you prefer hands-on work, research, or design</li>
                </ul>
                <p style="margin-top: 15px;">
                    <em>This chatbot uses AI to provide academic guidance. Always verify information with official UMD sources.</em>
                </p>
            </div>
        """)

        # Add feedback section
        with gr.Accordion("📝 Give Feedback on Last Response", open=False):
            with gr.Row():
                rating = gr.Radio(
                    choices=["👍 Helpful", "👎 Not Helpful", "🤔 Partially Helpful"], 
                    label="How was the response?",
                    value=None
         )
            feedback_text = gr.Textbox(
                label="Additional feedback (optional)", 
                placeholder="Tell us what could be improved...",
                lines=3
        )
            feedback_submit = gr.Button("Submit Feedback", variant="secondary")
            feedback_status = gr.Textbox(label="Status", interactive=False, visible=False)

    return interface

def save_feedback(user_message, bot_response, rating, feedback_text, history):
    """Save feedback to CSV file"""
    feedback_data = {
        'timestamp': datetime.now().isoformat(),
        'user_message': user_message,
        'bot_response': bot_response[:200] + "..." if len(bot_response) > 200 else bot_response,
        'rating': rating,
        'feedback_text': feedback_text,
        'tracked_interests': ', '.join(user_profile['interests'])
    }
    
    # Create CSV file if it doesn't exist
    csv_file = 'chatbot_feedback.csv'
    file_exists = os.path.isfile(csv_file)
    
    with open(csv_file, 'a', newline='', encoding='utf-8') as file:
        fieldnames = ['timestamp', 'user_message', 'bot_response', 'rating', 'feedback_text', 'tracked_interests']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(feedback_data)
    
    return "✅ Thank you! Your feedback has been saved.", "", ""


# Launch the application 
if __name__ == "__main__":
   interface = create_interface()
   interface.launch(
       server_name="0.0.0.0",
       server_port=7860,
       share=True,
       debug=True
   )
