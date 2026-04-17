import pandas as pd
import streamlit as st


st.set_page_config(page_title="CareerMatch AI", page_icon="💼", layout="wide")


def parse_list_field(value):
    if pd.isna(value) or str(value).strip() == "":
        return []
    return [item.strip().lower() for item in str(value).split(",") if item.strip()]


@st.cache_data
def load_jobs():
    df = pd.read_csv("jobs.csv")
    df["required_skills_list"] = df["required_skills"].apply(parse_list_field)
    df["nice_to_have_skills_list"] = df["nice_to_have_skills"].apply(parse_list_field)
    return df


def compute_match_score(job, user_skills, preferred_role, preferred_location, experience_level, user_interests):
    score = 0
    reasons = []
    missing_skills = []

    required_skills = set(job["required_skills_list"])
    nice_skills = set(job["nice_to_have_skills_list"])

    matched_required = required_skills.intersection(user_skills)
    matched_nice = nice_skills.intersection(user_skills)
    missing_required = required_skills.difference(user_skills)

    # Skill overlap
    if len(required_skills) > 0:
        skill_score = (len(matched_required) / len(required_skills)) * 50
        score += skill_score
    else:
        skill_score = 0

    if matched_required:
        reasons.append(f"matches key required skills like {', '.join(list(matched_required)[:3])}")

    if matched_nice:
        score += min(10, len(matched_nice) * 3)
        reasons.append(f"also aligns with bonus skills like {', '.join(list(matched_nice)[:2])}")

    # Role match
    if preferred_role and preferred_role.lower() == str(job["role_type"]).lower():
        score += 20
        reasons.append("fits the preferred role type")

    # Location match
    if preferred_location and preferred_location.lower() == str(job["location"]).lower():
        score += 10
        reasons.append("matches the preferred location")

    # Experience match
    if experience_level and experience_level.lower() == str(job["experience_level"]).lower():
        score += 10
        reasons.append("is aligned with the selected experience level")

    # Industry/interest match
    if user_interests and str(job["industry"]).lower() in user_interests:
        score += 10
        reasons.append("connects with the selected industry interest")

    # Penalty if too many required skills are missing
    if len(missing_required) >= max(3, len(required_skills) // 2 + 1):
        score -= 8

    missing_skills = sorted(list(missing_required))
    score = max(0, min(100, round(score)))
    return score, reasons, missing_skills


def build_recommendations(df, user_skills, preferred_role, preferred_location, experience_level, user_interests):
    recommendations = []

    for _, job in df.iterrows():
        score, reasons, missing_skills = compute_match_score(
            job,
            user_skills,
            preferred_role,
            preferred_location,
            experience_level,
            user_interests,
        )

        if reasons:
            explanation = (
                f"This role is a good match because it " + ", ".join(reasons[:3]) + "."
            )
        else:
            explanation = "This role has some partial overlap with your profile."

        recommendations.append(
            {
                "title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "role_type": job["role_type"],
                "industry": job["industry"],
                "experience_level": job["experience_level"],
                "description": job["description"],
                "score": score,
                "explanation": explanation,
                "missing_skills": missing_skills,
                "required_skills": job["required_skills"],
            }
        )

    rec_df = pd.DataFrame(recommendations).sort_values(by="score", ascending=False).reset_index(drop=True)
    return rec_df


def summarize_skill_gaps(recommendations_df):
    all_missing = []
    for skills in recommendations_df["missing_skills"].head(5):
        all_missing.extend(skills)

    if not all_missing:
        return []

    gap_counts = pd.Series(all_missing).value_counts()
    return list(gap_counts.head(5).index)


jobs_df = load_jobs()

st.title("💼 CareerMatch AI")
st.write(
    "A personalized job recommendation agent that ranks jobs based on your skills, interests, "
    "experience level, and preferences."
)

with st.sidebar:
    st.header("Your Profile")

    skills_input = st.text_area(
        "Skills",
        placeholder="Example: Python, SQL, data visualization, machine learning, dashboards",
        height=120,
    )

    preferred_role = st.selectbox(
        "Preferred Role Type",
        ["", "Data Analyst", "Software Engineer", "ML Engineer", "Business Analyst", "Product Analyst"],
    )

    preferred_location = st.selectbox(
        "Preferred Location",
        ["", "San Diego", "Remote", "New York", "San Francisco", "Chicago"],
    )

    experience_level = st.selectbox(
        "Experience Level",
        ["", "Internship", "Entry-Level", "Mid-Level"],
    )

    user_interests = st.multiselect(
        "Industry Interests",
        ["finance", "healthcare", "sports", "e-commerce", "education", "consumer tech"],
    )

    recommend_clicked = st.button("Find Matching Jobs", use_container_width=True)

if "run_recommendation" not in st.session_state:
    st.session_state.run_recommendation = False

if recommend_clicked:
    st.session_state.run_recommendation = True

if not st.session_state.run_recommendation:
    st.info("Fill in your profile on the left, then click **Find Matching Jobs**.")
    st.subheader("Sample use case")
    st.write(
        "Try skills like: Python, SQL, dashboards, analytics, machine learning, A/B testing"
    )
else:
    user_skills = {skill.strip().lower() for skill in skills_input.split(",") if skill.strip()}

    if not user_skills:
        st.warning("Please enter at least a few skills to generate recommendations.")
    else:
        rec_df = build_recommendations(
            jobs_df,
            user_skills,
            preferred_role,
            preferred_location,
            experience_level,
            set(user_interests),
        )

        top_recs = rec_df.head(5)

        col1, col2, col3 = st.columns(3)
        col1.metric("Jobs Evaluated", len(rec_df))
        col2.metric("Top Match Score", f"{int(top_recs.iloc[0]['score'])}%")
        col3.metric("Recommended Jobs", len(top_recs))

        st.markdown("## Top Job Matches")

        for _, row in top_recs.iterrows():
            with st.container(border=True):
                left, right = st.columns([3, 1])

                with left:
                    st.subheader(f"{row['title']} — {row['company']}")
                    st.write(f"**Location:** {row['location']}")
                    st.write(f"**Role Type:** {row['role_type']}")
                    st.write(f"**Industry:** {row['industry']}")
                    st.write(f"**Experience Level:** {row['experience_level']}")
                    st.write(f"**Why it matches:** {row['explanation']}")
                    st.write(f"**Job Description:** {row['description']}")

                    if row["missing_skills"]:
                        st.write(f"**Missing Skills:** {', '.join(row['missing_skills'][:5])}")
                    else:
                        st.write("**Missing Skills:** None of the major required skills appear to be missing.")

                with right:
                    st.metric("Match Score", f"{row['score']}%")
                    st.progress(int(row["score"]))

        st.markdown("## Skill Gap Insights")
        top_gaps = summarize_skill_gaps(top_recs)

        if top_gaps:
            st.write(
                "These are the most common skills missing from your top matches:"
            )
            for gap in top_gaps:
                st.write(f"- {gap}")
        else:
            st.success("You already match most of the major skills for your top recommendations.")

        st.markdown("## Recommendation Logic")
        st.write(
            "Jobs are ranked using a weighted score based on required skill overlap, role preference, "
            "location match, experience alignment, and industry interest."
        )

        st.markdown("## Full Job Dataset")
        display_df = jobs_df[["title", "company", "location", "role_type", "industry", "experience_level", "required_skills"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

)
