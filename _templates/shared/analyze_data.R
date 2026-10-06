# Canonical EDA code, shared by template_rmarkdown.Rmd and template_rnotebook.ipynb
# via updater.py. Sections are delimited by '# === SECTION: name ===' markers and
# spliced individually into each template's placeholders.

# === SECTION: glimpse ===
glimpse(df)

# === SECTION: str ===
str(df)

# === SECTION: head ===
head(df)

# === SECTION: tail ===
tail(df)

# === SECTION: clean_na ===
# Remove columns that have no values
df <- Filter(function(x) !all(is.na(x)), df)

# Remove rows with missing values (if appropriate)
df <- na.omit(df)

# === SECTION: sample_transposed ===
# display a small random sample transposed in order to see all variables
t(sample_n(df, 5))

# === SECTION: object_size ===
# the size of the data frame in memory
size <- object.size(df)
#  the size in bytes
print(size)

# === SECTION: summary_numeric ===
# describe numerical features
summary(df[, sapply(df, is.numeric)])

# === SECTION: summary_nonnumeric ===
# describe non-numerical features
summary(df[, sapply(df, Negate(is.numeric))])

# === SECTION: missing_tile ===
# check missing values
df %>%
  mutate(row = row_number()) %>%
  gather(key = "variable", value = "value", -row) %>%
  ggplot(aes(x = variable, y = row)) +
  geom_tile(aes(fill = is.na(value)), color = "black") +
  scale_fill_manual(values = c("TRUE" = "grey", "FALSE" = "red")) +
  labs(x = "", y = "", fill = "Missing") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

# === SECTION: histogram ===
# plot a histogram for each numerical feature
df %>%
  select_if(is.numeric) %>%
  gather() %>%
  ggplot( aes(value)) +
  geom_histogram(bins = 10, color = "white", fill = "red") +
    facet_wrap(~key, scales = 'free_x')
