"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_user_views.py


from app import app, CURR_USER_KEY
import os
from unittest import TestCase

from models import db, connect_db, Message, User, Likes, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app


# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class UserViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        testuser = User.signup(username="testuser",
                               email="test@test.com",
                               password="testuser",
                               image_url=None)

        self.u1 = User.signup("abc", "test1@test.com", "password", None)
        self.u2 = User.signup("efg", "test2@test.com", "password", None)
        self.u3 = User.signup("hij", "test3@test.com", "password", None)
        self.u4 = User.signup("testing", "test4@test.com", "password", None)

        db.session.commit()

        self.testuser = testuser

    def tearDown(self):

        db.session.rollback()

    def test_users_index(self):
        """Testing for the users we created to show"""
        with self.client as c:
            resp = c.get("/users")

            self.assertIn("@testuser", str(resp.data))
            self.assertIn("@abc", str(resp.data))
            self.assertIn("@efg", str(resp.data))
            self.assertIn("@hij", str(resp.data))
            self.assertIn("@testing", str(resp.data))

    def test_users_search(self):
        """Testing for the seach query to show the correct users"""
        with self.client as c:
            resp = c.get("/users?q=test")

            self.assertIn("@testuser", str(resp.data))
            self.assertIn("@testing", str(resp.data))

            self.assertNotIn("@abc", str(resp.data))
            self.assertNotIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))

    def test_user_show(self):
        """Testing for the correct user to show"""
        with self.client as c:
            resp = c.get(f"/users/{self.testuser.id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("@testuser", str(resp.data))

            self.assertNotIn("@hij", str(resp.data))

    def setup_likes(self):
        """Function to create messages and like"""
        message1 = Message(text="trending warble", user_id=self.testuser.id)
        message2 = Message(text="Eating some lunch", user_id=self.testuser.id)
        message3 = Message(id=9876, text="likable warble", user_id=self.u1.id)
        db.session.add_all([message1, message2, message3])
        db.session.commit()

        like1 = Likes(user_id=self.testuser.id, message_id=9876)

        db.session.add(like1)
        db.session.commit()

    def test_add_like(self):
        """Testing if the like is working"""
        message = Message(id=1984, text="The earth is round",
                          user_id=self.u1.id)
        db.session.add(message)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post("/users/add_like/1984", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id == 1984).all()
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].user_id, self.testuser.id)

    def test_remove_like(self):
        """Testing if removing the like works"""
        self.setup_likes()

        message = Message.query.filter(Message.text == "likable warble").one()
        self.assertIsNotNone(message)
        self.assertNotEqual(message.user_id, self.testuser.id)

        likes = Likes.query.filter(
            Likes.user_id == self.testuser.id and Likes.message_id == message.id
        ).one()

        # Now we are sure that testuser likes the message "likable warble"
        self.assertIsNotNone(likes)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post(
                f"/users/add_like/{message.id}", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id == message.id).all()
            # the like has been deleted
            self.assertEqual(len(likes), 0)

    def test_unauthenticated_like(self):
        """Testing for the like not to be removed if it's unauthorized"""
        self.setup_likes()

        message = Message.query.filter(Message.text == "likable warble").one()
        self.assertIsNotNone(message)

        like_count = Likes.query.count()

        with self.client as c:
            resp = c.post(
                f"/users/add_like/{message.id}", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            self.assertIn("Access unauthorized", str(resp.data))

            # The number of likes has not changed since making the request
            self.assertEqual(like_count, Likes.query.count())

    def setup_followers(self):
        """Function to setup followers"""
        f1 = Follows(user_being_followed_id=self.u1.id,
                     user_following_id=self.testuser.id)
        f2 = Follows(user_being_followed_id=self.u2.id,
                     user_following_id=self.testuser.id)
        f3 = Follows(user_being_followed_id=self.testuser.id,
                     user_following_id=self.u1.id)

        db.session.add_all([f1, f2, f3])
        db.session.commit()

    def test_show_following(self):
        """Testing if the following list is displayed"""

        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get(f"/users/{self.testuser.id}/following")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("@abc", str(resp.data))
            self.assertIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))
            self.assertNotIn("@testing", str(resp.data))

    def test_show_followers(self):
        """Testing if the followers list is displayed"""

        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get(f"/users/{self.testuser.id}/followers")

            self.assertIn("@abc", str(resp.data))
            self.assertNotIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))
            self.assertNotIn("@testing", str(resp.data))

    def test_unauthorized_following_page_access(self):
        """Testing if the following list is displayed when unauthorized"""
        self.setup_followers()
        with self.client as c:

            resp = c.get(
                f"/users/{self.testuser.id}/following", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("@abc", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))

    def test_unauthorized_followers_page_access(self):
        """Testing if the followers list is displayed when unauthorized"""
        self.setup_followers()
        with self.client as c:

            resp = c.get(
                f"/users/{self.testuser.id}/followers", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("@abc", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))
