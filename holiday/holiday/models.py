from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db.models import (BooleanField,
                              CharField,
                              DateTimeField,
                              EmailField,
                              ForeignKey,
                              GenericIPAddressField,
                              ManyToManyField,
                              Model,
                              OneToOneField,
                              PositiveSmallIntegerField,
                              URLField)


from smart_selects.db_fields import ChainedForeignKey


class ProgramType(Model):
    program_type = CharField(max_length=100, verbose_name='program type')

    def __unicode__(self):
        return self.program_type


class Program(Model):
    program_type = ManyToManyField(ProgramType)
    program_name = CharField(max_length=150, verbose_name='program name')
    program_site = URLField(max_length=200, verbose_name='program website')
    adopt_group_only = BooleanField(default=False,
                                    verbose_name='Available to adopt entire program only?')
    available_for_sponsorship = BooleanField(verbose_name="Available for sponsorship?",
                                             default=True)

    class Meta:
        ordering = ('program_name', )

    def __unicode__(self):
        return self.program_name


class ProgramMaximumChildren(Model):
    program = OneToOneField(Program)
    maximum_children = PositiveSmallIntegerField()

    class Meta:
        verbose_name_plural = "Programs with children limits"
        ordering = ('program', )

    def __unicode__(self):
        return self.program.__unicode__() + " max: " + str(self.maximum_children)


class WishlistItemCategory(Model):
    position = PositiveSmallIntegerField(
        "Position", default=0, blank=True, null=True)
    category = CharField(max_length=50)

    class Meta:
        verbose_name_plural = "Wishlist item categories"

    def __unicode__(self):
        return self.category


class ProgramStaff(Model):
    user = OneToOneField(User)
    first_login = BooleanField(default=True,
                               verbose_name='First login? (force user to reset password)')
    # must be nullable so save will work
    program = ForeignKey(Program, null=True)
    phone_number = CharField(max_length=15, blank=True, null=True)

    def __unicode__(self):
        return self.user.__unicode__() + ' with ' + self.program.program_name


class DirectorMultiPrograms(Model):
    """For directors of multilple programs."""
    director = OneToOneField(ProgramStaff)
    programs = ManyToManyField(Program, blank=True)

    class Meta:
        verbose_name_plural = "Directors of multiple programs"

    def __unicode__(self):
        return self.director.user.__unicode__() + ', director of mulitple programs'


class WishlistItem(Model):
    category = ForeignKey(WishlistItemCategory)
    position = PositiveSmallIntegerField(
        "Position", default=0, blank=True, null=True)
    item_name = CharField(max_length=100, verbose_name='item name')

    class Meta:
        ordering = ('position', )

    def __unicode__(self):
        return self.item_name


class ClothingSizeCategory(Model):
    id = CharField(max_length=1, primary_key=True)
    position = PositiveSmallIntegerField(
        "Position", default=0, blank=True, null=True)
    size_category = CharField(
        max_length=20, verbose_name="clothing size category")

    class Meta:
        verbose_name_plural = "Clothing Size Categories"
        ordering = ('position', )

    def __unicode__(self):
        return self.size_category


class ClothingSize(Model):
    size_category = ForeignKey(ClothingSizeCategory)
    position = PositiveSmallIntegerField(
        "Position", default=0, blank=True, null=True)
    clothing_size = CharField(
        max_length=50, verbose_name='clothing size description')

    class Meta:
        ordering = ('position', )

    def __unicode__(self):
        return self.size_category.size_category + " " + self.clothing_size


class Family(Model):
    staff_entering = ForeignKey(settings.AUTH_USER_MODEL, editable=False)
    program = ForeignKey(Program)
    available_for_sponsorship = BooleanField(verbose_name="Available for sponsorship?",
                                             default=False, editable=False)
    keep_available = BooleanField(verbose_name="Keep availabe for sponsorship?",
                                  default=False)
    keep_unavailable = BooleanField(verbose_name="Keep unavailabe for sponsorship?",
                                    default=False)
    approved = BooleanField(
        verbose_name="Approved by program director?", default=False)
    urgent_need = BooleanField(
        verbose_name="Is this family in urgent need?", default=False)

    class Meta:
        verbose_name_plural = "Families"

    def __unicode__(self):
        return self.program.program_name + ' family ID ' + str(self.id)


class Child(Model):
    GENDER_OPTIONS = (
        ('M', 'Male'),
        ('F', 'Female')
    )

    date_entered = DateTimeField(
        'date taken', auto_now_add=True, editable=False)
    staff_entering = ForeignKey(settings.AUTH_USER_MODEL, editable=False)
    approved = BooleanField(
        verbose_name="Approved by program director?", default=False)
    available_for_sponsorship = BooleanField(verbose_name="Available for sponsorship?",
                                             default=False, editable=False)
    keep_available = BooleanField(verbose_name="Keep availabe for sponsorship?",
                                  default=False)
    keep_unavailable = BooleanField(verbose_name="Keep unavailabe for sponsorship?",
                                    default=False)
    urgent_need = BooleanField(
        verbose_name="Is this child in urgent need?", default=False)
    first_name = CharField(max_length=50)
    gender = CharField(max_length=1, choices=GENDER_OPTIONS,
                       verbose_name="gender")
    age = PositiveSmallIntegerField(verbose_name="age",
                                    validators=[MinValueValidator(0), MaxValueValidator(25)])
    family = ForeignKey(Family, null=True, blank=True,
                        verbose_name="Family (can leave blank)")
    program = ForeignKey(Program)
    size_category = ForeignKey(
        ClothingSizeCategory, verbose_name="clothing size category")
    clothing_size = ChainedForeignKey(ClothingSize, chained_field="size_category",
                                      chained_model_field="size_category", show_all=False)
    wishlist_items = ManyToManyField(WishlistItem, through='WishlistChild')

    class Meta:
        verbose_name_plural = "Children"

    def search_description(self):
        # Do not display name on visitor site
        return self.get_gender_display() + ', ' + str(self.age) + ' years old'

    def __unicode__(self):
        return self.first_name + ' - ' + self.get_gender_display() + ', ' + \
            str(self.age) + ' years old'


class WishlistChild(Model):
    category = ForeignKey(WishlistItemCategory)
    item = ChainedForeignKey(WishlistItem, chained_field="category",
                             chained_model_field="category", show_all=False, null=True, blank=True)
    # item = GroupedForeignKey(WishlistItem, "category", null=True, blank=True)
    child = ForeignKey(Child)
    have_other = BooleanField(default=False)
    other_item = CharField(max_length=100, null=True, blank=True)
    notes = CharField(max_length=200, null=True, blank=True)

    def __unicode__(self):
        desc = ''
        if self.category:
            desc += self.category.category + ': '

        if self.item:
            desc += self.item.item_name + ' '

        if self.other_item:
            desc += self.other_item

        return desc


class GeneralWishlistItem(Model):
    category = ForeignKey(WishlistItemCategory)
    item = ChainedForeignKey(WishlistItem, chained_field="category",
                             chained_model_field="category", show_all=False, null=True, blank=True)
    position = PositiveSmallIntegerField(
        "Position", default=0, blank=True, null=True)
    have_other = BooleanField(default=False)
    other_item = CharField(max_length=100, null=True, blank=True)
    notes = CharField(max_length=200, null=True, blank=True)
    quantity = PositiveSmallIntegerField(default=1)
    quantity_pledged = PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ('position', )

    def __unicode__(self):
        desc = ''
        if self.category:
            desc += self.category.category + ': '

        if self.item:
            desc += self.item.item_name + ' '

        if self.other_item:
            desc += self.other_item

        desc += '(' + str(self.quantity) + ' requested)'
        return desc


class State(Model):
    st_abbr = CharField(max_length=2, primary_key=True)
    state_name = CharField(max_length=100, verbose_name='State')

    class Meta:
        ordering = ('state_name', )

    def __unicode__(self):
        return self.state_name


def validate_zip_code(value):
    if len(value) != 5 and len(value) != 10:
        raise ValidationError(
            u'This field should be a five-digit zip code, or a zip+4.')


def validate_phone(value):
    if len(value) > 0 and len(value) != 14:
        raise ValidationError(
            u'This field should be a U.S. phone number, with area code.')


class Donor(Model):
    date_entered = DateTimeField('date taken', auto_now_add=True, editable=False, blank=True,
                                 null=True)
    entered_from_address = GenericIPAddressField(unpack_ipv4=True, blank=True,
                                                 null=True, editable=False)
    first_name = CharField(max_length=200)
    last_name = CharField(max_length=200)
    company_name = CharField(max_length=200, blank=True, null=True,
                             verbose_name="Company name (optional)")
    email_address = EmailField(max_length=200)
    street_address1 = CharField(
        max_length=150, verbose_name="street address line 1")
    street_address2 = CharField(max_length=150, null=True, blank=True,
                                verbose_name="street address line 2")
    city = CharField(max_length=100, verbose_name='city')
    state = ForeignKey(State)
    zip_code = CharField(max_length=10, validators=[validate_zip_code])
    phone_number = CharField(max_length=15, blank=True, null=True,
                             validators=[validate_phone], verbose_name="Phone number (optional)")
    adopted_children = ManyToManyField(Child, blank=True)
    adopted_families = ManyToManyField(Family, blank=True)
    adopted_programs = ManyToManyField(Program, blank=True)
    adopted_wishlist = ManyToManyField(GeneralWishlistItem, through='DonorGeneralWishlist',
                                       verbose_name="Adopted wishlist items", blank=True)

    def __unicode__(self):
        return self.first_name + " " + self.last_name + " in " + self.city


class DonorGeneralWishlist(Model):
    donor = ForeignKey(Donor)
    wishlist_item = ForeignKey(GeneralWishlistItem)
    quantity = PositiveSmallIntegerField()

    def __unicode__(self):
        desc = self.donor.first_name + " " + self.donor.last_name + \
            " sponsors " + str(self.quantity) + " of "
        if self.wishlist_item.item:
            desc += self.wishlist_item.item.item_name
        else:
            desc += self.wishlist_item.other_item
        return desc
