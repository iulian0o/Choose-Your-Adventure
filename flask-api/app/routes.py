from flask import Blueprint, request, jsonify
from . import db
from .models import Story, Page, Choice

bp = Blueprint("api", __name__)


@bp.route("/stories", methods=["GET"])
def get_stories():
    """Get all stories, optionally filtered by status"""
    status = request.args.get("status")

    if status:
        stories = Story.query.filter_by(status=status).all()
    else:
        stories = Story.query.all()

    return jsonify([story.to_dict() for story in stories])


@bp.route("/stories/<int:story_id>", methods=["GET"])
def get_story(story_id):
    """Get a specific story by ID"""
    story = Story.query.get_or_404(story_id)
    return jsonify(story.to_dict())


@bp.route("/stories", methods=["POST"])
def create_story():
    # Create a new story
    data = request.json

    story = Story(
        title=data.get("title"),
        description=data.get("description"),
        status=data.get("status", "published"),
        author_id=data.get("author_id"),
    )

    db.session.add(story)
    db.session.commit()

    return jsonify(story.to_dict()), 201


@bp.route("/stories/<int:story_id>", methods=["PUT"])
def update_story(story_id):
    # Update an existing story
    story = Story.query.get_or_404(story_id)
    data = request.json

    story.title = data.get("title", story.title)
    story.description = data.get("description", story.description)
    story.status = data.get("status", story.status)
    story.start_page_id = data.get("start_page_id", story.start_page_id)
    story.illustration = data.get("illustration", story.illustration)

    db.session.commit()

    return jsonify(story.to_dict())


@bp.route("/stories/<int:story_id>", methods=["DELETE"])
def delete_story(story_id):
    # Delete a story
    story = Story.query.get_or_404(story_id)

    Page.query.filter_by(story_id=story_id).delete()

    db.session.delete(story)
    db.session.commit()

    return jsonify({"message": "Story deleted successfully"}), 200


@bp.route("/stories/<int:story_id>/start", methods=["GET"])
def get_story_start(story_id):
    # Get the starting page of a story
    story = Story.query.get_or_404(story_id)

    if not story.start_page_id:
        return jsonify({"error": "Story has no starting page"}), 404

    start_page = Page.query.get(story.start_page_id)

    return jsonify(start_page.to_dict())


@bp.route("/pages/<int:page_id>", methods=["GET"])
def get_page(page_id):
    # Get a specific page with its choices
    page = Page.query.get_or_404(page_id)
    return jsonify(page.to_dict())


@bp.route("/stories/<int:story_id>/pages", methods=["POST"])
def create_page(story_id):
    # Create a new page for a story
    story = Story.query.get_or_404(story_id)
    data = request.json

    page = Page(
        story_id=story_id,
        text=data.get("text"),
        is_ending=data.get("is_ending", False),
        ending_label=data.get("ending_label"),
        illustration=data.get("illustration"),
    )

    db.session.add(page)
    db.session.commit()

    if not story.start_page_id:
        story.start_page_id = page.id
        db.session.commit()

    return jsonify(page.to_dict()), 201


@bp.route("/pages/<int:page_id>", methods=["PUT"])
def update_page(page_id):
    # Update a page
    page = Page.query.get_or_404(page_id)
    data = request.json

    page.text = data.get("text", page.text)
    page.is_ending = data.get("is_ending", page.is_ending)
    page.ending_label = data.get("ending_label", page.ending_label)
    page.illustration = data.get("illustration", page.illustration)

    db.session.commit()

    return jsonify(page.to_dict())


@bp.route("/pages/<int:page_id>", methods=["DELETE"])
def delete_page(page_id):
    # Delete a page
    page = Page.query.get_or_404(page_id)

    db.session.delete(page)
    db.session.commit()

    return jsonify({"message": "Page deleted successfully"}), 200


@bp.route("/pages/<int:page_id>/choices", methods=["POST"])
def create_choice(page_id):
    # Create a new choice for a page
    page = Page.query.get_or_404(page_id)
    data = request.json

    choice = Choice(
        page_id=page_id,
        text=data.get("text"),
        next_page_id=data.get("next_page_id"),
        requires_dice_roll=data.get("requires_dice_roll", False),
        dice_threshold=data.get("dice_threshold"),
    )

    db.session.add(choice)
    db.session.commit()

    return jsonify(choice.to_dict()), 201


@bp.route("/choices/<int:choice_id>", methods=["PUT"])
def update_choice(choice_id):
    # Update a choice
    choice = Choice.query.get_or_404(choice_id)
    data = request.json

    choice.text = data.get("text", choice.text)
    choice.next_page_id = data.get("next_page_id", choice.next_page_id)
    choice.requires_dice_roll = data.get(
        "requires_dice_roll", choice.requires_dice_roll
    )
    choice.dice_threshold = data.get("dice_threshold", choice.dice_threshold)

    db.session.commit()

    return jsonify(choice.to_dict())


@bp.route("/choices/<int:choice_id>", methods=["DELETE"])
def delete_choice(choice_id):
    # Delete a choice
    choice = Choice.query.get_or_404(choice_id)

    db.session.delete(choice)
    db.session.commit()

    return jsonify({"message": "Choice deleted successfully"}), 200


@bp.route("/stories/<int:story_id>/tree", methods=["GET"])
def get_story_tree(story_id):
    # Get the full story tree for visualization
    story = Story.query.get_or_404(story_id)
    pages = Page.query.filter_by(story_id=story_id).all()

    tree_data = {"story": story.to_dict(), "pages": [page.to_dict() for page in pages]}

    return jsonify(tree_data)
