from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch.dispatcher import receiver
from django.template.context import Context
from django.utils.translation import ugettext_lazy as _
from voting.models import Vote
from open_municipio.newscache.models import News
import datetime
import sys


class CommentWithMood(Comment):
    POSITIVE = '+'
    NEGATIVE = '-'
    NEUTRAL = '0'
    MOOD_CHOICES = (
        (POSITIVE, _('Positive')),
        (NEGATIVE, _('Negative')),
        (NEUTRAL, _('Neutral')),                      
    )
    
    mood = models.CharField(_("Comment mood"), max_length=1, choices=MOOD_CHOICES, default=NEUTRAL)    

    class Meta:
        verbose_name = "Comment"


#
# Signals handlers
#

#
# Signals handlers
#

@receiver(post_save, sender=CommentWithMood)
@receiver(post_save, sender=Vote)
def new_comment(**kwargs):
    """
    generates a record in newscache, when someone votes on something
    """

    # generates news only if not in raw mode (fixtures)
    # and for objects creation
    if not kwargs.get('raw', False) and kwargs.get('created', False):
        generating_item = kwargs['instance']
        object = generating_item.content_object
        user = generating_item.user.get_profile()
        # define context for textual representation of the news
        ctx = Context({ 'object': object, 'user': user })

        # two news are generated

        # the first news is related to the act, and generated only once per day,
        # when the first user votes the object

        # get today's datetime, at midnight
        t = datetime.datetime.today()
        d = datetime.datetime(year=t.year, month=t.month, day=t.day)

        # get list of all dates with news generated by comments,
        # related to the commented object's instance
        news_grouped_by_date = News.objects.filter(
            generating_content_type=ContentType.objects.get_for_model(generating_item),
            related_content_type=ContentType.objects.get_for_model(object),
            related_object_pk=object.pk
        ).dates('created', 'day')

        sender = ContentType.objects.get_for_model(generating_item)
        if sender.model == 'commentwithmood':
            template_particle = 'comment'
        elif sender.model == 'vote':
            template_particle = 'vot'
        else:
            raise ObjectDoesNotExist

        # generate news only if no news were already generated today
        if d not in news_grouped_by_date:
            News.objects.create(
                generating_object=generating_item, related_object=object,
                priority=2, news_type=News.NEWS_TYPE.community,
                text=News.get_text_for_news(ctx, 'newscache/object_%sed.html' % template_particle)
            )

        # the second news is related to the commenting user, with priority 2
        News.objects.create(
            generating_object=generating_item, related_object=user,
            priority=2, news_type=News.NEWS_TYPE.community,
            text=News.get_text_for_news(ctx, 'newscache/user_%sing.html' % template_particle)
        )


@receiver(pre_delete, sender=Vote)
def removed_comment(**kwargs):
    """
    removes records in newscache, when someone stops monitoring something
    """
    generating_item = kwargs['instance']
    object = generating_item.content_object
    user = generating_item.user.get_profile()

    # first remove news related to the monitored object
    News.objects.filter(
        generating_content_type=ContentType.objects.get_for_model(generating_item),
        generating_object_pk = generating_item.pk,
        related_content_type=ContentType.objects.get_for_model(object),
        related_object_pk=object.pk
    ).delete()
    # second remove news related to the monitoring user
    News.objects.filter(
        generating_content_type=ContentType.objects.get_for_model(generating_item),
        generating_object_pk = generating_item.pk,
        related_content_type=ContentType.objects.get_for_model(user),
        related_object_pk=user.pk
    ).delete()
