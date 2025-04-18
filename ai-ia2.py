from openai import OpenAI
from secret import OPENAI_API_KEY
import pandas as pd
import re

client = OpenAI(api_key=OPENAI_API_KEY)

def format_console_text(text):
    return re.sub(r"\*\*(.*?)\*\*", r"\033[1;34m\1\033[0m", text)

def ask_gpt(prompt, temperature=0.7):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful educational quiz assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature
    )
    return response.choices[0].message.content

def generate_quiz(topic, prev_performance=None):
    prompt = f"""
    Act as an expert tutor on the topic: "{topic}".

    Generate 5 unique, non-repetitive, and medium-to-hard level multiple choice questions.
    Rules:
    - Application or concept-based (no simple facts).
    - 4 options (A to D), only one correct answer.
    - Strict format:

    Q1. Question text?
    A. Option A
    B. Option B
    C. Option C
    D. Option D
    Answer: B

    {f"The user previously struggled with: {prev_performance}" if prev_performance else ""}
    """
    return ask_gpt(prompt)

def parse_questions(raw_text):
    questions = []
    raw_blocks = re.split(r"\n(?=Q\d+\.)", raw_text.strip())

    for block in raw_blocks:
        try:
            q_match = re.search(r"Q\d+\.\s*(.*)", block)
            question_line = q_match.group(1).strip() if q_match else None

            options = {}
            for letter in ['A', 'B', 'C', 'D']:
                match = re.search(rf"{letter}\.\s*(.*)", block)
                if match:
                    options[letter] = match.group(1).strip()

            answer_match = re.search(r"Answer:\s*([A-D])", block)
            answer = answer_match.group(1).strip() if answer_match else None

            if question_line and len(options) == 4 and answer:
                questions.append({
                    "question": question_line,
                    "options": options,
                    "answer": answer
                })
            else:
                print(f"⚠️ Skipping malformed block:\n{block}\n")

        except Exception as e:
            print(f"⚠️ Error parsing block:\n{block}\nError: {e}\n")

    return questions

def take_quiz(questions):
    responses = []
    for idx, q in enumerate(questions):
        print(f"\nQ{idx+1}: {q['question']}")
        for key, val in q['options'].items():
            print(f"  {key}. {val}")
        user_ans = input("Your answer (A/B/C/D): ").strip().upper()
        correct = user_ans == q['answer']
        explanation_raw = ask_gpt(f"""Explain why the correct answer to this question is {q['answer']}:
        Q: {q['question']}
        Options: {q['options']}
        """)
        explanation = format_console_text(explanation_raw)
        print(f"{'✅ Correct' if correct else '❌ Incorrect'}, Answer: {q['answer']}")
        print(f"\033[1mExplanation:\033[0m {explanation}\n")  # Bold Explanation
        responses.append({
            "question": q['question'],
            "your_answer": user_ans,
            "correct_answer": q['answer'],
            "is_correct": correct,
            "explanation": explanation_raw
        })
    return responses

def final_feedback(topic, responses):
    incorrects = [r for r in responses if not r['is_correct']]
    weak_points = "\n".join([r['question'] for r in incorrects])
    prompt = f"""
    The user attempted a 10-question quiz on the topic "{topic}".

    They struggled with the following:
    {weak_points}

    Please:
    - Summarize their weak areas
    - Recommend what to study
    - Suggest learning resources (YouTube, websites, etc.)
    """
    raw_feedback = ask_gpt(prompt)
    return format_console_text(raw_feedback)

topic = input("📘 Enter the topic you want to be quizzed on: ")
print("\n🔹 Generating 5 initial questions...\n")
quiz1_raw = generate_quiz(topic)
quiz1 = parse_questions(quiz1_raw)
results1 = take_quiz(quiz1)

incorrect_topics = "\n".join([r['question'] for r in results1 if not r['is_correct']])
print("\n🔹 Generating 5 follow-up adaptive questions...\n")
quiz2_raw = generate_quiz(topic, prev_performance=incorrect_topics)
quiz2 = parse_questions(quiz2_raw)
results2 = take_quiz(quiz2)

all_results = results1 + results2
df = pd.DataFrame(all_results)
df.to_csv("quiz_results.csv", index=False)
print("\n📁 Results saved to quiz_results.csv")

print("\n\033[1;31m### Response:\033[0m\n")
feedback = final_feedback(topic, all_results)
print(feedback)