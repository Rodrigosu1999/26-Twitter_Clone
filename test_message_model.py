"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


from app import app
import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows, Likes

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


class MessageModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        user = User.signup(
            "test_user", "test_email@email.com", "test_password", None)
        db.session.commit()

        self.user = user

        self.client = app.test_client()

    def tearDown(self):
        """Clean up any fouled transaction."""

        db.session.rollback()

    def test_message_model(self):
        """Does basic model work?"""

        message = Message(
            text="testing",
            user_id=self.user.id
        )

        db.session.add(message)
        db.session.commit()

        # User should have 1 message
        self.assertEqual(len(self.user.messages), 1)
        # The message should be the one we set
        self.assertEqual(self.user.messages[0].text, "testing")
        # The message's user_id should be the same than our user's id
        self.assertEqual(message.user_id, self.user.id)

    def test_message_likes(self):
        """Testing if the likes work between messages and users"""

        # We are creating two messages to test
        message1 = Message(
            text="testing",
            user_id=self.user.id
        )

        message2 = Message(
            text="second test",
            user_id=self.user.id
        )

        # We are creaiting a second user as the first user can't like it's own messages (this is controlled in app.py)
        user2 = User.signup(
            "test_user2", "test_email2@email.com", "test_password2", None)

        db.session.add_all([message1, message2, user2])
        db.session.commit()
        # We are making our second user like the user 1 message
        user2.likes.append(message1)

        db.session.commit()
        # Here we get the user2 list of liked messages
        likes = Likes.query.filter(Likes.user_id == user2.id).all()
        # We should only have on like
        self.assertEqual(len(likes), 1)
        # The liked message id should be the same as the one we set
        self.assertEqual(likes[0].message_id, message1.id)
        # We are checking that the message is not the one we set
        self.assertIsNot(likes[0].message_id, message2.id)
