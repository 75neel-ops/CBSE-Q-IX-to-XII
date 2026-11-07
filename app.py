import os
import streamlit as st
from google import genai
from json_repair import repair_json
import json
import re

# Page Configuration
st.set_page_config(
    page_title="CBSE Q IX to XII",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Gemini Client securely using Streamlit Secrets
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
elif os.environ.get("GEMINI_API_KEY"):
    api_key = os.environ.get("GEMINI_API_KEY")

client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Failed to initialize Gemini Client: {e}")

# Chapter/topic lists follow the CBSE curriculum for 2026-27.
# Classes IX-X use integrated Science; topics are grouped by discipline.
CHAPTERS_BY_CLASS_SUBJECT = {
    ("Class IX", "Mathematics"): ["Number System", "Introduction to Polynomials", "Sequences and Progressions", "Exploring Algebraic Identities", "Linear Equations in Two Variables", "Coordinate Geometry", "Introduction to Euclid’s Geometry: Axioms and Postulates", "Lines and Angles", "Triangles – Congruence Theorems", "4-gons (Quadrilaterals)", "Circles", "Area and Perimeter", "Surface Area and Volume", "Statistics", "Introduction to Probability"],
    ("Class IX", "Physics"): ["Exploration: Entering the World of Secondary Science", "Motion", "Force and Laws of Motion", "Work, Energy and Simple Machines", "Sound", "Earth as a System: Energy, Matter and Life"],
    ("Class IX", "Chemistry"): ["Exploration: Entering the World of Secondary Science", "Exploring Mixtures and Their Separation", "Structure of an Atom", "Atoms and Molecules", "Earth as a System: Energy, Matter and Life"],
    ("Class IX", "Biology"): ["Exploration: Entering the World of Secondary Science", "Cell", "Tissues", "Reproduction", "Diversity", "Earth as a System: Energy, Matter and Life"],
    ("Class X", "Mathematics"): ["Real Numbers", "Polynomials", "Pair of Linear Equations in Two Variables", "Quadratic Equations", "Arithmetic Progressions", "Triangles", "Coordinate Geometry", "Introduction to Trigonometry", "Some Applications of Trigonometry", "Circles", "Areas Related to Circles", "Surface Areas and Volumes", "Statistics", "Probability"],
    ("Class X", "Physics"): ["Light: Reflection and Refraction", "The Human Eye and the Colourful World", "Electricity", "Magnetic Effects of Electric Current", "Electric Motors, Electromagnetic Induction and Electric Generator (formative)"],
    ("Class X", "Chemistry"): ["Chemical Reactions and Equations", "Periodic Classification of Elements (formative)", "Acids, Bases and Salts (formative)", "Metals and Non-metals (formative)", "Carbon and its Compounds (formative)"],
    ("Class X", "Biology"): ["Life Processes", "Control and Co-ordination in Animals and Plants", "Reproduction", "Heredity (formative)", "Evolution (formative)", "Our Environment"],
    ("Class XI", "Mathematics"): ["Sets", "Relations and Functions", "Trigonometric Functions", "Complex Numbers and Quadratic Equations", "Linear Inequalities", "Permutations and Combinations", "Binomial Theorem", "Sequence and Series", "Straight Lines", "Conic Sections", "Introduction to Three-dimensional Geometry", "Limits and Derivatives", "Statistics", "Probability"],
    ("Class XI", "Physics"): ["Units and Measurements", "Motion in a Straight Line", "Motion in a Plane", "Laws of Motion", "Work, Energy and Power", "System of Particles and Rotational Motion", "Gravitation", "Mechanical Properties of Solids", "Mechanical Properties of Fluids", "Thermal Properties of Matter", "Thermodynamics", "Kinetic Theory", "Oscillations", "Waves"],
    ("Class XI", "Chemistry"): ["Some Basic Concepts of Chemistry", "Structure of Atom", "Classification of Elements and Periodicity in Properties", "Chemical Bonding and Molecular Structure", "Chemical Thermodynamics", "Equilibrium", "Redox Reactions", "Organic Chemistry: Some Basic Principles and Techniques", "Hydrocarbons"],
    ("Class XI", "Biology"): ["The Living World", "Biological Classification", "Plant Kingdom", "Animal Kingdom", "Morphology of Flowering Plants", "Anatomy of Flowering Plants", "Structural Organisation in Animals", "Cell: The Unit of Life", "Biomolecules", "Cell Cycle and Cell Division", "Photosynthesis in Higher Plants", "Respiration in Plants", "Plant Growth and Development", "Breathing and Exchange of Gases", "Body Fluids and Circulation", "Excretory Products and their Elimination", "Locomotion and Movement", "Neural Control and Coordination", "Chemical Coordination and Integration"],
    ("Class XII", "Mathematics"): ["Relations and Functions", "Inverse Trigonometric Functions", "Matrices", "Determinants", "Continuity and Differentiability", "Applications of Derivatives", "Integrals", "Applications of Integrals", "Differential Equations", "Vector Algebra", "Three-dimensional Geometry", "Linear Programming", "Probability"],
    ("Class XII", "Physics"): ["Electric Charges and Fields", "Electrostatic Potential and Capacitance", "Current Electricity", "Moving Charges and Magnetism", "Magnetism and Matter", "Electromagnetic Induction", "Alternating Current", "Electromagnetic Waves", "Ray Optics and Optical Instruments", "Wave Optics", "Dual Nature of Radiation and Matter", "Atoms", "Nuclei", "Semiconductor Electronics: Materials, Devices and Simple Circuits"],
    ("Class XII", "Chemistry"): ["Solutions", "Electrochemistry", "Chemical Kinetics", "d- and f-Block Elements", "Coordination Compounds", "Haloalkanes and Haloarenes", "Alcohols, Phenols and Ethers", "Aldehydes, Ketones and Carboxylic Acids", "Amines", "Biomolecules"],
    ("Class XII", "Biology"): ["Sexual Reproduction in Flowering Plants", "Human Reproduction", "Reproductive Health", "Principles of Inheritance and Variation", "Molecular Basis of Inheritance", "Evolution", "Human Health and Diseases", "Microbes in Human Welfare", "Biotechnology: Principles and Processes", "Biotechnology and its Applications", "Organisms and Populations", "Ecosystem", "Biodiversity and its Conservation"],
}

# Sidebar - CBSE Configuration & Owner Info
with st.sidebar:
    st.title("📚 CBSE Q IX to XII")
    st.markdown("---")
    st.markdown("### ⚙️ Question Paper Setup")
    
    # Configuration Options
    selected_class = st.selectbox("Select Class", ["Class IX", "Class X", "Class XI", "Class XII"])
    selected_subject = st.selectbox("Select Subject", ["Mathematics", "Physics", "Chemistry", "Biology"])
    
    # Conditional subject-specific question type options
    physics_focus = "Standard"
    chemistry_focus = "Standard"
    if selected_subject == "Physics":
        physics_focus = st.radio(
            "Physics Focus Type:",
            ["Maths of Physics", "Questions without maths"]
        )
    elif selected_subject == "Chemistry":
        chemistry_focus = st.radio(
            "Chemistry Question Type:",
            ["Maths", "Questions without maths"]
        )

    chapter_options = CHAPTERS_BY_CLASS_SUBJECT.get((selected_class, selected_subject), [])
    chapter_choice = st.selectbox(
        "Choose Chapter",
        ["— Select a chapter —", *chapter_options, "Other / enter chapter name"],
        help=(
            "For Classes IX and X, CBSE Science is integrated; these lists group its "
            "chapters by topic. Items marked formative are for practice, not the "
            "year-end examination."
        ),
    )
    if chapter_choice == "Other / enter chapter name":
        chapter_name = st.text_input("Enter Chapter Name", placeholder="Type another chapter or topic")
    elif chapter_choice == "— Select a chapter —":
        chapter_name = ""
    else:
        chapter_name = chapter_choice
    
    selected_marks = st.selectbox("Marks per Question", [1, 2, 3, 4, 5])
    selected_difficulty = st.selectbox("Difficulty Level", ["Easy", "Hard", "Extra Hard", "Tricky", "Analytical"])
    
    batch_size = st.slider("Questions per batch:", min_value=5, max_value=20, value=5, step=5)
    
    st.markdown("---")
    # Owner Badge
    st.markdown(
        f"<div style='text-align: center; color: #64748b; font-size: 0.85rem; padding: 10px; background: #f1f5f9; border-radius: 8px;'>"
        f"<b>Owner:</b> NilanjanC<br>Powered by Gemini 3.5 Flash-Lite"
        f"</div>",
        unsafe_allow_html=True
    )

# Main Application Header
st.title("CBSE Q IX to XII - AI Question Bank")
st.markdown("Generate custom CBSE-aligned NCERT practice questions with 3 options, hints, and detailed explanations.")

# Initialize session state for tracking questions and progress
if "asked_questions" not in st.session_state:
    st.session_state["asked_questions"] = []
if "quiz_data" not in st.session_state:
    st.session_state["quiz_data"] = None

def generate_cbse_quiz_batch():
    if not client:
        st.error("Gemini API key is missing! Please configure your secrets.toml.")
        return False
    if not chapter_name.strip():
        st.warning("Please enter a chapter name in the sidebar before generating questions.")
        return False
        
    with st.spinner(f"Generating {batch_size} CBSE-aligned questions for {chapter_name}..."):
        try:
            asked_list = st.session_state.get("asked_questions", [])
            excluded_text = "\n".join([f"- {q}" for q in asked_list]) if asked_list else "None yet."
            
            # Tailor subject instruction based on user selection
            if selected_subject == "Mathematics":
                subject_prompt_desc = f"Subject: Core CBSE Mathematics (Pure math problems, equations, theorems, and calculations for {selected_class}, Chapter: {chapter_name})."
            elif selected_subject == "Physics":
                if physics_focus == "Maths of Physics":
                    subject_prompt_desc = f"Subject: Physics - Numerical/Mathematical problem-solving involving formulas, calculations, and derivations for Chapter: {chapter_name} ({selected_class})."
                else:
                    subject_prompt_desc = f"Subject: Physics - Conceptual and theoretical questions WITHOUT numerical calculations for Chapter: {chapter_name} ({selected_class})."
            elif selected_subject == "Chemistry":
                if chemistry_focus == "Maths":
                    subject_prompt_desc = f"Subject: Chemistry calculation and numerical problem-solving, especially physical chemistry where relevant, for Chapter: {chapter_name}, {selected_class}."
                else:
                    subject_prompt_desc = f"Subject: Chemistry conceptual and theoretical questions without numerical calculations from Chapter: {chapter_name}, {selected_class}."
            else:
                subject_prompt_desc = f"Subject: Biology (Theoretical, diagram-based, or conceptual questions from Chapter: {chapter_name}, {selected_class})."

            prompt = f"""You are an expert CBSE curriculum question creator and examiner.
Generate exactly {batch_size} high-quality multiple-choice questions for:
- Class: {selected_class}
- {subject_prompt_desc}
- Marks Weightage: {selected_marks} Mark(s) per question
- Difficulty: {selected_difficulty}
- Guidelines: Strictly follow NCERT guidelines and CBSE exam patterns.

CRITICAL RULES:
1. Provide exactly 3 answer options (A, B, C) for each question.
2. Do NOT repeat or include any of these previously asked questions:
{excluded_text}
3. Return the output STRICTLY as a valid JSON array of objects with no markdown formatting outside it. Format:
[
  {{
    "question": "Question statement here",
    "options": ["A) ...", "B) ...", "C) ..."],
    "answer": "A",
    "hint": "Helpful clue without giving away the direct answer",
    "explanation": "Step-by-step CBSE-style solution explanation"
  }}
]"""

            response = client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=prompt,
            )
            
            response_text = response.text
            repaired_json_str = repair_json(response_text, return_objects=False)
            quiz_json = json.loads(repaired_json_str)
            
            for q in quiz_json:
                st.session_state["asked_questions"].append(q["question"])

            st.session_state["quiz_data"] = quiz_json
            st.session_state["quiz_submitted"] = False
            st.session_state["user_answers"] = {}
            return True
        except Exception as e:
            st.error(f"Error generating questions: {e}")
            with st.expander("Debug Raw AI Response"):
                st.text(response_text if 'response_text' in locals() else "No response generated")
            return False

# Action buttons & Workspace
sub_title_info = f"{selected_subject}"
if selected_subject == "Physics":
    sub_title_info += f" ({physics_focus})"
elif selected_subject == "Chemistry":
    sub_title_info += f" ({chemistry_focus})"

if not st.session_state.get("quiz_data"):
    if st.button("🚀 Generate CBSE Practice Quiz", type="primary", use_container_width=True):
        success = generate_cbse_quiz_batch()
        if success:
            st.rerun()
else:
    quiz_data = st.session_state["quiz_data"]
    st.markdown(f"### 📝 Practice Quiz: {chapter_name} ({selected_class} - {sub_title_info})")
    st.info(f"Difficulty: **{selected_difficulty}** | Marks per Question: **{selected_marks}** | Total Questions in Batch: **{len(quiz_data)}**")
    
    with st.form("cbse_quiz_form"):
        user_answers = {}
        for idx, q in enumerate(quiz_data):
            st.markdown(f"#### Q{idx + 1}: {q['question']}")
            
            # On-demand Hint Expander
            with st.expander(f"💡 Show Hint for Q{idx + 1}"):
                st.write(q['hint'])
            
            # 3 answer options radio buttons
            user_choice = st.radio(
                f"Choose your answer for Q{idx + 1}:",
                q['options'],
                key=f"cbse_q_{idx}_{len(st.session_state['asked_questions'])}_{idx}"
            )
            user_answers[idx] = user_choice
            st.markdown("---")
        
        submitted = st.form_submit_button("Submit Answers & Evaluate", type="primary")
        
    if submitted:
        st.session_state["quiz_submitted"] = True
        st.session_state["user_answers"] = user_answers

    if st.session_state.get("quiz_submitted", False):
        st.markdown("### 📊 Evaluation & Detailed Solutions")
        correct_count = 0
        wrong_count = 0
        user_answers = st.session_state.get("user_answers", {})
        
        for idx, q in enumerate(quiz_data):
            selected = user_answers.get(idx, "")
            selected_letter = selected[0].upper() if selected else ""
            correct_letter = str(q['answer']).strip().upper()
            
            is_correct = (selected_letter == correct_letter)
            if is_correct:
                correct_count += 1
            else:
                wrong_count += 1
            
            st.markdown(f"**Q{idx + 1}:** {q['question']}")
            st.markdown(f"Your Answer: `{selected}`")
            
            if is_correct:
                st.success("✅ Correct Answer!")
            else:
                st.error(f"❌ Incorrect. The correct option is **Option {correct_letter}**.")
            
            st.info(f"**Explanation:** {q['explanation']}")
            st.markdown("---")
        
        # Scorecard metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Right Answers", value=correct_count)
        with col2:
            st.metric(label="Wrong Answers", value=wrong_count)
        with col3:
            total_score = correct_count * selected_marks
            max_score = len(quiz_data) * selected_marks
            st.metric(label="Score Earned", value=f"{total_score} / {max_score}")
        
        st.markdown("---")
        if st.button("➡️ Load Next Lot of Questions", type="primary"):
            success = generate_cbse_quiz_batch()
            if success:
                st.rerun()
