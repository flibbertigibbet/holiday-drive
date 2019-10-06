import django
from django.forms import (ChoiceField, Form, ModelForm, ModelChoiceField, ModelMultipleChoiceField,
                          MultipleHiddenInput)
from django.forms.widgets import HiddenInput, CheckboxInput, RadioSelect
from holiday.models import (Child, DirectorMultiPrograms, Donor, GeneralWishlistItem, Program,
                            ProgramType, WishlistChild, WishlistItemCategory)
from django.forms.models import BaseInlineFormSet


class DonorItemsForm(Form):
    items = ModelMultipleChoiceField(queryset=GeneralWishlistItem.objects.all(),
                                     widget=django.forms.MultipleHiddenInput)
    quantity = django.forms.IntegerField(widget=django.forms.HiddenInput)


class SponsorInformation(ModelForm):
    class Meta:
        model = Donor
        fields = ('first_name', 'last_name', 'company_name', 'email_address', 'street_address1',
                  'street_address2', 'city', 'state', 'zip_code', 'phone_number',
                  'adopted_children', 'adopted_families', 'adopted_programs')

        widgets = {'adopted_children': MultipleHiddenInput,
                   'adopted_families': MultipleHiddenInput,
                   'adopted_programs': MultipleHiddenInput}


class DirectorSwitchProgram(Form):
    programs = ModelChoiceField(
        queryset=Program.objects.all(), label='Switch program')

    def __init__(self, director=None, *args, **kwargs):
        super(DirectorSwitchProgram, self).__init__(*args, **kwargs)
        if director:
            programs = DirectorMultiPrograms.objects.filter(id=director).values_list('programs',
                                                                                     flat=True)
            self.fields['programs'].queryset = Program.objects.filter(
                id__in=programs)


class InitialProgramDirector(Form):
    first_name = django.forms.CharField(max_length=30, min_length=1)
    last_name = django.forms.CharField(max_length=30, min_length=1)
    phone_number = django.forms.CharField(max_length=15, min_length=10)


class SearchKidName(Form):
    child_name = django.forms.CharField(max_length=30, min_length=1)


class SearchChildren(Form):
    # urgent_need = ChoiceField(required=False, choices=(("", "---------"),
    #  ('T', "Children in urgent need"), ('F', "Children not in urgent need")))
    gender = ChoiceField(required=False, choices=(("", "---------"),
                                                  ("M", "Boys"), ("F", "Girls")))
    age_range = ChoiceField(required=False, choices=(("", "---------"),
                                                     ("0", "0 to 4 years old"),
                                                     ("1", "5 to 9 years old"),
                                                     ("2", "10 to 14 years old"),
                                                     ("3", "15 to 19 years old"),
                                                     ("4", "20 to 25 years old")))
    program_type = ModelChoiceField(
        required=False, queryset=ProgramType.objects.all())

    widgets = {'gender': RadioSelect}


class SearchFamilies(Form):
    # urgent_need = ChoiceField(required=False, choices=(("", "---------"),
    #  ('T', "Families in urgent need"), ('F', "Families not in urgent need")))
    family_size = ChoiceField(required=False, choices=(("", "---------"),
                                                       ("2", "Two children"),
                                                       ("3", "Three children"),
                                                       ("4", "Four children"),
                                                       ("5", "Five or more children")))
    program_type = ModelChoiceField(
        required=False, queryset=ProgramType.objects.all())


class SearchGeneral(Form):
    # filter to categories with general wishlist items
    item_category = ModelChoiceField(required=False,
                                     queryset=WishlistItemCategory.objects.filter(
                                         id__in=GeneralWishlistItem.objects.values_list('category')))


class SearchPrograms(Form):
    program_type = ModelChoiceField(
        required=False, queryset=ProgramType.objects.all())


class ChildWishlistFormSet(BaseInlineFormSet):
    class Meta:
        model = WishlistChild
        fields = ('category', 'item', 'have_other', 'other_item', 'notes')
        widgets = {'have_other': CheckboxInput, }

    def clean(self):
        super(ChildWishlistFormSet, self).clean()
        # if any(self.errors):
        #   return

        count_non_giftcard = 0
        count_non_empty = 0
        for form in self.forms:
            if form.cleaned_data:
                cat = form.cleaned_data.get('category')
                have_other = form.cleaned_data.get('have_other')
                other_item = form.cleaned_data.get('other_item')
                item = form.cleaned_data.get('item')
                if not item and not have_other:
                    form._errors['item'] = self.error_class([
                        u'Please select an item from the list, or enter something for "other item."'])
                elif have_other and not other_item:
                    form._errors['other_item'] = self.error_class([
                        u'Please enter a description for the item here.'])

                if cat is None:
                    count_non_giftcard += 1
                elif cat.category != 'Gift Card':
                    count_non_giftcard += 1

                count_non_empty += 1

            else:
                form._errors['item'] = self.error_class([
                    u'Please select an item from the list, or enter something for "other item."'])

        if count_non_giftcard < 1:
            print("raising error")
            raise django.forms.ValidationError(
                'Please enter at least one wishlist item that is not a gift card.',
                code='invalid')

        # if count_non_empty < 2:
        #   raise django.forms.ValidationError('Please enter at least two wishlist items.',
        #     code='invalid')


class ChildPage1(ModelForm):
    class Meta:
        model = Child
        fields = ('id', 'first_name', 'gender', 'age',
                  'family', 'size_category', 'clothing_size')
        widgets = {'id': HiddenInput}
