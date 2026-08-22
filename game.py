from datetime import datetime, timezone, timedelta
import random

class GameManager:
    VOTING_SECONDS = 30

    def __init__(self, database):
        self.db = database

    # STATE
    def get_state(self):
        return self.db.get_game_state()

    # QUESTIONS
    def get_unused_questions(self):
        questions = self.db.get_questions()
        return [q for q in questions if not q["used"]]

    def start_random_question(self):
        unused = self.get_unused_questions()

        if not unused:
            return False

        question = random.choice(unused)
        self.start_question(question["id"])
        return True

    def start_question(self, question_id, duration=None):
        if duration is None:
            duration = self.VOTING_SECONDS

        end_time = datetime.now(timezone.utc) + timedelta(seconds=duration)
        self.db.mark_question_used(question_id)

        self.db.update_game_state({
            "status": "voting",
            "current_question_id": question_id,
            "voting_ends_at": end_time.isoformat(),
            "question_type": None,
            "score_applied": False,
            "paused_remaining_seconds": None
        })

    # TIMER
    def get_remaining_seconds(self, state=None):
        if state is None:
            state = self.get_state()

        if not state:
            return 0

        if state["status"] == "paused":
            remaining = state.get("paused_remaining_seconds")

            if remaining is None:
                return 0

            return max(0, int(remaining))

        voting_ends_at = state.get("voting_ends_at")

        if not voting_ends_at:
            return 0

        end_time = datetime.fromisoformat(voting_ends_at.replace("Z", "+00:00"))

        remaining = int((end_time - datetime.now(timezone.utc)).total_seconds())
        return max(0, remaining)

    # PAUSE
    def pause(self):
        state = self.get_state()

        if state["status"] != "voting":
            return False

        remaining = self.get_remaining_seconds(state)

        self.db.update_game_state({
            "status": "paused",
            "paused_remaining_seconds": remaining
        })

        return True

    # RESUME
    def resume(self):
        state = self.get_state()

        if state["status"] != "paused":
            return False

        remaining = state.get("paused_remaining_seconds")

        if remaining is None:
            remaining = 0

        end_time = datetime.now(timezone.utc) + timedelta(seconds=int(remaining))

        self.db.update_game_state({
            "status": "voting",
            "voting_ends_at": end_time.isoformat(),
            "paused_remaining_seconds": None
        })

        return True

    # CLOSE VOTING
    def close_voting(self):
        self.db.update_game_state({"status": "result"})

    # SKIP
    def skip_question(self):
        state = self.get_state()
        current_id = state.get("current_question_id")

        if current_id is not None:
            self.db.mark_question_used(current_id)

        unused = [q for q in self.get_unused_questions() if q["id"] != current_id]

        if unused:
            next_question = random.choice(unused)
            self.start_question(next_question["id"])
            return True

        self.db.update_game_state({
            "status": "finished",
            "current_question_id": None,
            "voting_ends_at": None,
            "paused_remaining_seconds": None
        })

        return False

    # QUESTION TYPE
    def set_question_type(self, question_type):
        self.db.update_game_state({"question_type": question_type})

    # SCORE
    def apply_scores(self, question_id, question_type):
        state = self.get_state()

        if state["score_applied"]:
            return False

        votes = self.db.get_votes(question_id)
        counts = {}

        for vote in votes:
            name = vote["selected_name"]
            counts[name] = counts.get(name, 0) + 1

        multiplier = -1 if question_type == "negative" else 1

        for name, count in counts.items():
            student = self.db.get_student(name)

            if student:
                current_score = student.get("score") or 0
                new_score = current_score + count * multiplier
                self.db.update_student_score(name, new_score)

        self.db.update_game_state({"score_applied": True})

        return True

    # NEXT QUESTION
    def next_question(self):
        unused = self.get_unused_questions()

        if not unused:
            self.finish_game()
            return False

        question = random.choice(unused)
        self.start_question(question["id"])

        return True

    # FINISH
    def finish_game(self):
        self.db.update_game_state({
            "status": "finished",
            "current_question_id": None,
            "voting_ends_at": None,
            "paused_remaining_seconds": None
        })

    # RESET
    def reset_game(self):
        self.db.reset_votes()
        self.db.reset_questions()
        self.db.reset_students()
        self.db.update_game_state({
            "status": "waiting",
            "current_question_id": None,
            "voting_ends_at": None,
            "question_type": None,
            "score_applied": False,
            "paused_remaining_seconds": None
        })