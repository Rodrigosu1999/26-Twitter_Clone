"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


from app import app, CURR_USER_KEY
import os
from unittest import TestCase

from models import db, connect_db, Message, User

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


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        testuser = User.signup(username="testuser",
                               email="test@test.com",
                               password="testuser",
                               image_url=None)

        db.session.commit()
        self.testuser = testuser

    def test_add_message(self):
        """Can user add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_add_message_no_session(self):
        """Testing that we don't add a message when there is no user in session"""
        with self.client as c:
            resp = c.post("/messages/new",
                          data={"text": "Hello"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_add_message_invalid_user(self):
        """Testing when we are giving an invalid user id"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = 1234

            resp = c.post("/messages/new",
                          data={"text": "Hello"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_message_show(self):
        """Testing for the message to show"""

        message = Message(
            id=1234,
            text="a test message",
            user_id=self.testuser.id
        )

        db.session.add(message)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            message = Message.query.get(1234)

            resp = c.get(f'/messages/{message.id}')

            self.assertEqual(resp.status_code, 200)
            self.assertIn(message.text, str(resp.data))

    def test_invalid_message_show(self):
        """Testing to get a 404 when we try to se a emssage that doesn't exist"""
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get('/messages/1234')

            self.assertEqual(resp.status_code, 404)

    def test_message_delete(self):
        """Testing delete message function"""

        message = Message(
            id=1234,
            text="a test message",
            user_id=self.testuser.id
        )
        db.session.add(message)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post("/messages/1234/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            message = Message.query.get(1234)
            self.assertIsNone(message)

    def test_unauthorized_message_delete(self):
        """Testing when a user tries to delete a message that is not his"""

        # A second user that will try to delete the message
        user = User.signup(username="unauthorized-user",
                           email="testtest@test.com",
                           password="password",
                           image_url=None)
        user.id = 1234

        # Message is owned by testuser
        message = Message(
            id=12345,
            text="a test message",
            user_id=self.testuser.id
        )
        db.session.add_all([user, message])
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = 1234

            resp = c.post("/messages/12345/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))
            # The message should still exist as we didn't delete it
            message = Message.query.get(12345)
            self.assertIsNotNone(message)

    def test_message_delete_no_authentication(self):
        """Testing when a user tries to delete a message when he is not logged in"""
        message = Message(
            id=1234,
            text="a test message",
            user_id=self.testuser.id
        )
        db.session.add(message)
        db.session.commit()

        with self.client as c:
            resp = c.post("/messages/1234/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))
            # The message should still exist as we didn't delete it
            message = Message.query.get(1234)
            self.assertIsNotNone(message)
