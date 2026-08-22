from datetime import datetime, timezone
from supabase import create_client

class Database:
    def __init__(self, url, key):
        self.supabase = create_client(url, key)

    # STUDENTS
    def get_students(self):
        response = self.supabase.table("students").select("*").order("name").execute()
        return response.data or []

    def get_student(self, name):
        response = self.supabase.table("students").select("*").eq("name", name).single().execute()
        return response.data

    def mark_student_joined(self, student):
        try:
            self.supabase.table("students").update({
                "joined_at": datetime.now(timezone.utc).isoformat()
            }).eq(
                "name",
                student
            ).execute()

            return True

        except Exception:
            return False

    def get_joined_students_count(self):
        try:
            response = self.supabase.table("students").select("name").not_.is_("joined_at", "null").execute()
            return len(response.data or [])

        except Exception:
            return 0

    def reset_students(self):
        try:
            self.supabase.table("students").update({
                "score": 0,
                "joined_at": None
            }).neq(
                "id",
                0
            ).execute()

        except Exception:
            self.supabase.table("students").update({
                "score": 0
            }).neq(
                "id",
                0
            ).execute()

    def update_student_score(self, name, score):
        self.supabase.table("students").update({
            "score": score
        }).eq(
            "name",
            name
        ).execute()

    # QUESTIONS
    def get_questions(self):
        response = self.supabase.table("questions").select("*").order("id").execute()
        return response.data or []

    def get_question(self, question_id):
        if question_id is None:
            return None

        response = self.supabase.table("questions").select("*").eq("id", question_id).single().execute()
        return response.data

    def get_student_question(self, student):
        response = self.supabase.table("questions").select("*").eq("created_by", student).limit(1).execute()

        if response.data:
            return response.data[0]

        return None

    def add_question(self, question, student):
        existing = self.get_student_question(student)

        if existing:
            return False

        try:
            self.supabase.table("questions").insert({
                "question": question,
                "created_by": student,
                "used": False
            }).execute()

            return True

        except Exception:
            return False

    def mark_question_used(self, question_id):
        self.supabase.table("questions").update({
            "used": True
        }).eq(
            "id",
            question_id
        ).execute()

    # GAME STATE
    def get_game_state(self):
        response = self.supabase.table("game_state").select("*").eq("id", 1).single().execute()
        return response.data

    def update_game_state(self, data):
        return self.supabase.table("game_state").update(data).eq("id", 1).execute()

    # VOTES
    def get_votes(self, question_id):
        response = self.supabase.table("votes").select("*").eq("question_id", question_id).execute()
        return response.data or []

    def has_voted(self, question_id, student):
        response = (
            self.supabase
            .table("votes")
            .select("id")
            .eq("question_id", question_id)
            .eq("voter_name", student)
            .limit(1)
            .execute()
        )

        return bool(response.data)

    def submit_vote(self, question_id, voter, selected):
        if self.has_voted(question_id, voter):
            return False

        try:
            self.supabase.table("votes").insert({
                "question_id": question_id,
                "voter_name": voter,
                "selected_name": selected
            }).execute()

            return True

        except Exception:
            return False

    # SCORES
    def get_vote_counts(self, question_id):
        votes = self.get_votes(question_id)
        counts = {}

        for vote in votes:
            name = vote["selected_name"]
            counts[name] = counts.get(name, 0) + 1

        return counts

    def reset_votes(self):
        self.supabase.table("votes").delete().neq("id", 0).execute()

    def reset_questions(self):
        self.supabase.table("questions").delete().neq("id", 0).execute()